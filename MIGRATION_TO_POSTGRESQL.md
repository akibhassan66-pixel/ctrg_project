# PostgreSQL Migration Status

The local MySQL database `ctrg_grant_system` was migrated into the local PostgreSQL server on April 16, 2026.

## Current PostgreSQL connection

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "ctrg_grant_system",
        "USER": "ctrg_app",
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": "127.0.0.1",
        "PORT": "5432",
    }
}
```

Use your own local or hosted PostgreSQL password through environment variables or a local `.env` file. Do not commit real credentials.

## Migration artifacts

- `mysql_backup.sql`
- `ctrg_mysql_to_postgres.load`
- `mysql_dump_to_postgres.py`
- `postgres_import.sql`

## What was done

1. Exported MySQL with `mysqldump`.
2. Created PostgreSQL role `ctrg_app`.
3. Created PostgreSQL database `ctrg_grant_system`.
4. Converted the MySQL dump to PostgreSQL SQL.
5. Imported the converted SQL into PostgreSQL with `psql`.

## Remaining runtime note

The repo's checked-in `venv` is still broken on this machine. The database migration is done, but Django will only run after you use a working Python environment with the dependencies from `requirements.txt`.
