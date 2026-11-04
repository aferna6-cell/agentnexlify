# Postgres off-site backup

Railway cron image for a nightly `pg_dump` of Supabase. The service root
directory is this folder. Leave the start command empty so the image
entrypoint (`/opt/venv/bin/python /app/backup.py`) runs.

Do not add `railway.json` or `railway.toml` here. A second Railway config
file can override the API service.

Operator steps, environment variables, and restore commands:
`docs/ops/postgres-offsite-backup.md`.

PR Validation collects the tests under `tests/`:

```bash
python3 -m pytest tests/test_postgres_offsite_backup.py tests/test_postgres_offsite_restore.py -q
```
