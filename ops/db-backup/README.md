# Postgres off-site backup

Railway cron image for a nightly `pg_dump` of Supabase. The service root
directory is this folder. Leave the start command empty so the image
entrypoint (`/opt/venv/bin/python /app/backup.py`) runs.

Do not add `railway.json` or `railway.toml` here. A second Railway config
file can override the API service.

Operator steps, environment variables, and restore commands:
`docs/ops/postgres-offsite-backup.md`.

Local restore test (starts Postgres on 127.0.0.1 only; not collected by CI):

```bash
python3 -m pytest ops/db-backup/tests -q
```
