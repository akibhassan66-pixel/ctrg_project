from __future__ import annotations

import re
import sys
from hashlib import sha1
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Raw:
    text: str


def q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def scoped_name(table_name: str, object_name: str) -> str:
    base = f"{table_name}_{object_name}"
    if len(base) <= 63:
        return base
    suffix = sha1(base.encode("utf-8")).hexdigest()[:8]
    return f"{base[:54]}_{suffix}"


def quote_backticks(text: str) -> str:
    return re.sub(r"`([^`]+)`", lambda match: q(match.group(1)), text)


def strip_mysql_comments(sql_text: str) -> str:
    kept = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped:
            kept.append("")
            continue
        if stripped.startswith("--"):
            continue
        if stripped.startswith("/*!") and stripped.endswith("*/;"):
            continue
        kept.append(line)
    return "\n".join(kept)


def split_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_string = False
    escaped = False

    for char in sql_text:
        current.append(char)
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "'":
                in_string = False
            continue

        if char == "'":
            in_string = True
            continue

        if char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []

    trailing = "".join(current).strip()
    if trailing:
        statements.append(trailing)
    return statements


def clean_attrs(attrs: str) -> str:
    attrs = re.sub(r"CHARACTER SET\s+\w+", "", attrs, flags=re.IGNORECASE)
    attrs = re.sub(r"COLLATE\s+\w+", "", attrs, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", attrs).strip()


def split_type_and_attrs(rest: str) -> tuple[str, str]:
    depth = 0
    for index, char in enumerate(rest):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == " " and depth == 0:
            type_part = rest[:index]
            attrs = rest[index + 1 :].strip()
            if attrs.lower().startswith("unsigned"):
                type_part = f"{type_part} unsigned"
                attrs = attrs[8:].strip()
            return type_part.strip(), attrs
    return rest.strip(), ""


def convert_type(mysql_type: str) -> tuple[str, str]:
    mysql_type = mysql_type.lower()
    boolean_kind = "boolean" if mysql_type == "tinyint(1)" else "other"

    if mysql_type == "tinyint(1)":
        return "boolean", boolean_kind
    if mysql_type.startswith("enum("):
        return "text", boolean_kind
    if mysql_type.startswith("varchar("):
        return mysql_type, boolean_kind
    if mysql_type.startswith("char("):
        return mysql_type, boolean_kind
    if mysql_type.startswith("decimal("):
        return mysql_type.replace("decimal", "numeric", 1), boolean_kind
    if mysql_type.startswith("datetime"):
        return "timestamp", boolean_kind
    if mysql_type == "date":
        return "date", boolean_kind
    if mysql_type == "text" or mysql_type == "longtext":
        return "text", boolean_kind
    if mysql_type == "int":
        return "integer", boolean_kind
    if mysql_type == "int unsigned":
        return "bigint", boolean_kind
    if mysql_type == "bigint":
        return "bigint", boolean_kind
    if mysql_type == "bigint unsigned":
        return "numeric(20,0)", boolean_kind
    if mysql_type == "smallint unsigned":
        return "integer", boolean_kind
    if mysql_type == "smallint":
        return "smallint", boolean_kind
    return mysql_type, boolean_kind


def convert_default(default_value: str, kind: str) -> str | None:
    raw = default_value.strip()
    raw = re.sub(r"(?<!\w)_\w+", "", raw)
    if raw.startswith("(") and raw.endswith(")"):
        raw = raw[1:-1].strip()
    if raw.upper() == "NULL":
        return None
    if kind == "boolean":
        if raw in {"1", "'1'"}:
            return "TRUE"
        if raw in {"0", "'0'"}:
            return "FALSE"
    return raw


def parse_column_line(line: str) -> tuple[str, str, str | None, bool]:
    match = re.match(r"`([^`]+)`\s+(.*)", line)
    if not match:
        raise ValueError(f"Unable to parse column line: {line}")

    column_name = match.group(1)
    mysql_rest = clean_attrs(match.group(2))
    mysql_type, attrs = split_type_and_attrs(mysql_rest)
    pg_type, kind = convert_type(mysql_type)
    identity = "AUTO_INCREMENT" in attrs.upper()
    attrs = re.sub(r"\bAUTO_INCREMENT\b", "", attrs, flags=re.IGNORECASE).strip()

    default_match = re.search(r"\bDEFAULT\b\s+(.+?)(?=\s+NOT NULL|\s+NULL|\s+ON UPDATE|\s*$)", attrs, flags=re.IGNORECASE)
    default_sql = None
    if default_match:
        default_sql = convert_default(default_match.group(1), kind)
        attrs = attrs[: default_match.start()] + attrs[default_match.end() :]
        attrs = attrs.strip()

    not_null = "NOT NULL" in attrs.upper()

    parts = [q(column_name), pg_type]
    if identity:
        parts.append("GENERATED BY DEFAULT AS IDENTITY")
    if default_sql is not None:
        parts.append(f"DEFAULT {default_sql}")
    if not_null:
        parts.append("NOT NULL")

    return column_name, " ".join(parts), kind, identity


def convert_create_table(
    statement: str,
) -> tuple[str, list[str], list[str], list[dict[str, object]], list[tuple[str, str]]]:
    match = re.match(r"CREATE TABLE `([^`]+)` \((.*)\)\s*(ENGINE=.*)?$", statement, flags=re.S)
    if not match:
        raise ValueError(f"Unable to parse CREATE TABLE statement:\n{statement}")

    table_name = match.group(1)
    body = match.group(2)

    columns_sql: list[str] = []
    indexes_sql: list[str] = []
    foreign_keys_sql: list[str] = []
    columns_meta: list[dict[str, object]] = []
    identity_columns: list[tuple[str, str]] = []

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.endswith(","):
            line = line[:-1]

        if line.startswith("`"):
            column_name, pg_column, kind, identity = parse_column_line(line)
            columns_sql.append(pg_column)
            columns_meta.append({"name": column_name, "kind": kind})
            if identity:
                identity_columns.append((table_name, column_name))
            continue

        quoted = quote_backticks(line)
        if quoted.startswith("PRIMARY KEY"):
            columns_sql.append(quoted)
            continue

        unique_match = re.match(r'UNIQUE KEY "([^"]+)" \((.+)\)$', quoted)
        if unique_match:
            constraint_name = scoped_name(table_name, unique_match.group(1))
            columns_sql.append(f'CONSTRAINT {q(constraint_name)} UNIQUE ({unique_match.group(2)})')
            continue

        index_match = re.match(r'KEY "([^"]+)" \((.+)\)$', quoted)
        if index_match:
            index_name = scoped_name(table_name, index_match.group(1))
            indexes_sql.append(f'CREATE INDEX {q(index_name)} ON {q(table_name)} ({index_match.group(2)});')
            continue

        if quoted.startswith("CONSTRAINT "):
            if " FOREIGN KEY " in quoted:
                foreign_keys_sql.append(f"ALTER TABLE {q(table_name)} ADD {quoted};")
            else:
                columns_sql.append(quoted)
            continue

        raise ValueError(f"Unhandled CREATE TABLE line for {table_name}: {line}")

    create_sql = f"CREATE TABLE {q(table_name)} (\n  " + ",\n  ".join(columns_sql) + "\n);"
    return create_sql, indexes_sql, foreign_keys_sql, columns_meta, identity_columns


def parse_mysql_string(text: str, index: int) -> tuple[str, int]:
    assert text[index] == "'"
    index += 1
    chars: list[str] = []

    escape_map = {
        "0": "",
        "b": "\b",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "Z": "\x1a",
        "\\": "\\",
        "'": "'",
        '"': '"',
    }

    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 1
            if index >= len(text):
                break
            chars.append(escape_map.get(text[index], text[index]))
            index += 1
            continue
        if char == "'":
            return "".join(chars), index + 1
        chars.append(char)
        index += 1

    raise ValueError("Unterminated string literal in INSERT statement")


def parse_insert_rows(values_text: str) -> list[list[object]]:
    rows: list[list[object]] = []
    index = 0
    length = len(values_text)

    while index < length:
        while index < length and values_text[index] in " \r\n\t,":
            index += 1
        if index >= length:
            break
        if values_text[index] != "(":
            raise ValueError(f"Expected '(' at position {index}")

        index += 1
        row: list[object] = []

        while index < length:
            while index < length and values_text[index] in " \r\n\t":
                index += 1

            if values_text[index] == "'":
                value, index = parse_mysql_string(values_text, index)
                row.append(value)
            else:
                start = index
                while index < length and values_text[index] not in ",)":
                    index += 1
                token = values_text[start:index].strip()
                if token.upper() == "NULL":
                    row.append(None)
                else:
                    row.append(Raw(token))

            while index < length and values_text[index] in " \r\n\t":
                index += 1

            if index < length and values_text[index] == ",":
                index += 1
                continue

            if index < length and values_text[index] == ")":
                index += 1
                rows.append(row)
                break

            raise ValueError(f"Unexpected token while parsing row at position {index}")

    return rows


def quote_sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def render_value(value: object, kind: str | None) -> str:
    if value is None:
        return "NULL"
    if kind == "boolean":
        if isinstance(value, Raw):
            token = value.text
            if token in {"1", "'1'", "TRUE", "true"}:
                return "TRUE"
            if token in {"0", "'0'", "FALSE", "false"}:
                return "FALSE"
            if token.upper() == "NULL":
                return "NULL"
        if isinstance(value, str):
            if value == "1":
                return "TRUE"
            if value == "0":
                return "FALSE"
    if isinstance(value, Raw):
        return value.text
    return quote_sql_string(value)


def convert_insert(statement: str, table_columns: dict[str, list[dict[str, object]]]) -> str:
    match = re.match(r"INSERT INTO `([^`]+)` VALUES\s*(.+)$", statement, flags=re.S)
    if not match:
        raise ValueError(f"Unable to parse INSERT statement:\n{statement[:200]}")

    table_name = match.group(1)
    values_text = match.group(2).rstrip()
    if values_text.endswith(";"):
        values_text = values_text[:-1]
    rows = parse_insert_rows(values_text.strip())
    metadata = table_columns[table_name]

    rendered_rows = []
    for row in rows:
        if len(row) != len(metadata):
            raise ValueError(f"Column count mismatch for {table_name}: expected {len(metadata)}, got {len(row)}")
        rendered_values = [render_value(value, metadata[index]["kind"]) for index, value in enumerate(row)]
        rendered_rows.append("(" + ", ".join(rendered_values) + ")")

    return f"INSERT INTO {q(table_name)} VALUES\n" + ",\n".join(rendered_rows) + ";"


def build_sequence_sql(identity_columns: list[tuple[str, str]]) -> list[str]:
    statements = []
    for table_name, column_name in identity_columns:
        statements.append(
            "SELECT setval("
            f"pg_get_serial_sequence('{table_name}', '{column_name}'), "
            f"COALESCE((SELECT MAX({q(column_name)}) FROM {q(table_name)}), 1), "
            "true);"
        )
    return statements


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python mysql_dump_to_postgres.py <mysql_dump.sql> <postgres_output.sql>")
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    raw_bytes = input_path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "latin-1"):
        try:
            sql_text = raw_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"Unable to decode {input_path}")

    sql_text = strip_mysql_comments(sql_text)
    statements = split_statements(sql_text)

    table_columns: dict[str, list[dict[str, object]]] = {}
    identity_columns: list[tuple[str, str]] = []
    deferred_foreign_keys: list[str] = []
    output_statements = ["BEGIN;"]

    for statement in statements:
        stripped = statement.strip()
        if not stripped:
            continue

        upper = stripped.upper()
        if upper.startswith("SET "):
            continue
        if upper.startswith("LOCK TABLES") or upper.startswith("UNLOCK TABLES"):
            continue
        if upper.startswith("ALTER TABLE ") and ("DISABLE KEYS" in upper or "ENABLE KEYS" in upper):
            continue

        if upper.startswith("DROP TABLE IF EXISTS"):
            table_name = re.search(r"`([^`]+)`", stripped).group(1)
            output_statements.append(f"DROP TABLE IF EXISTS {q(table_name)} CASCADE;")
            continue

        if upper.startswith("CREATE TABLE"):
            create_sql, indexes_sql, foreign_keys_sql, columns_meta, table_identity_columns = convert_create_table(stripped)
            table_name = re.match(r"CREATE TABLE `([^`]+)`", stripped).group(1)
            table_columns[table_name] = columns_meta
            identity_columns.extend(table_identity_columns)
            deferred_foreign_keys.extend(foreign_keys_sql)
            output_statements.append(create_sql)
            output_statements.extend(indexes_sql)
            continue

        if upper.startswith("INSERT INTO"):
            output_statements.append(convert_insert(stripped, table_columns))
            continue

        raise ValueError(f"Unhandled statement:\n{stripped[:300]}")

    output_statements.extend(deferred_foreign_keys)
    output_statements.extend(build_sequence_sql(identity_columns))
    output_statements.append("COMMIT;")

    output_path.write_text("\n\n".join(output_statements) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
