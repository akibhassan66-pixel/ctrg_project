from django.db import connection


ACTIVE_CYCLE_TABLE = "school_active_cycles"


def ensure_active_cycle_table():
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ACTIVE_CYCLE_TABLE} (
                school_id integer PRIMARY KEY REFERENCES schools(school_id) ON DELETE CASCADE,
                cycle_id integer NOT NULL REFERENCES grantcycles(cycle_id) ON DELETE CASCADE,
                updated_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{ACTIVE_CYCLE_TABLE}_cycle_id
            ON {ACTIVE_CYCLE_TABLE} (cycle_id)
            """
        )


def get_active_cycle_id_for_school(school_id):
    if not school_id:
        return None

    ensure_active_cycle_table()
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT cycle_id FROM {ACTIVE_CYCLE_TABLE} WHERE school_id = %s",
            [school_id],
        )
        row = cursor.fetchone()
    return row[0] if row else None


def get_latest_active_cycle_entry():
    ensure_active_cycle_table()
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT school_id, cycle_id
            FROM {ACTIVE_CYCLE_TABLE}
            ORDER BY updated_at DESC, school_id ASC
            LIMIT 1
            """
        )
        row = cursor.fetchone()

    if not row:
        return None

    return {
        "school_id": row[0],
        "cycle_id": row[1],
    }


def set_active_cycle_for_school(school_id, cycle_id):
    ensure_active_cycle_table()
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO {ACTIVE_CYCLE_TABLE} (school_id, cycle_id, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (school_id)
            DO UPDATE SET
                cycle_id = EXCLUDED.cycle_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            [school_id, cycle_id],
        )


def attach_active_cycle_flags(cycles, school_id):
    active_cycle_id = get_active_cycle_id_for_school(school_id)
    for cycle in cycles:
        cycle.is_manual_active = cycle.cycle_id == active_cycle_id
    return active_cycle_id
