# Nightly Supabase Postgres backup image.
#
# Railway service root directory must be ops/db-backup so this file is the
# build context. Do not point the API service at this directory, and do not
# add a railway.toml here: a second Railway config file overrides the API
# service (see docs/dev-knowledge/bug-patterns.md, pattern 66).

FROM postgres:17-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        age \
        ca-certificates \
        python3 \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r /app/requirements.txt \
    && rm -rf /root/.cache

COPY backup_common.py backup.py restore.py /app/

RUN chown -R postgres:postgres /app
USER postgres

# Leave the Railway start command empty so this entrypoint is what runs.
# python3 on PATH is Debian's interpreter and does not have boto3 installed.
ENTRYPOINT ["/opt/venv/bin/python", "/app/backup.py"]
