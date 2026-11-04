# Nightly off-site Postgres backup

Supabase project `pxserpybmajixqrmzaly` is on the Free plan. That plan has no
restorable daily backups and no point-in-time recovery. This job is the copy
that can be restored.

The job is a separate Railway cron service. It runs `pg_dump` in custom
format with gzip compression level 6, encrypts the archive, and uploads it
to Cloudflare R2 or Backblaze B2. Age is the encryption to use.
`BACKUP_ENCRYPTION_KEY` is the other accepted key. If neither is set, the
job raises `ConfigError` and does not dump or upload. On failure it sends
one email through Resend and exits non-zero.

The job never deletes objects. Keep backups for 14 to 30 days with a bucket
lifecycle rule (21 days is the setting to use). The backup credential must
not have delete permission.

`pg_dump` only reads the source database. The script does not apply
migrations. Merging this repository change does not create the Railway
service, does not open a connection to Supabase, and does not change
production.

## Railway cron setup

Use a new service. Do not add a cron schedule to the API service, and do not
edit the root `railway.json`. A second `railway.toml` / `railway.json` can
override the API build (bug pattern 66). New Railway services also do not
read config-as-code, so the schedule is typed into the service settings.

After this pull request is merged to `main`:

1. Open the production Railway project. Choose **New → GitHub Repo** and select `aferna6-cell/agentnexlify`. Name the service `postgres-backup`. Connect it to `main`.
2. Open the new service **Settings → Source** and set **Root Directory** to `ops/db-backup` before the first successful deploy. That directory contains the backup `Dockerfile`. Leave the API service root directory alone.
3. **Settings → Deploy → Custom Start Command:** leave this empty. The image entrypoint is `/opt/venv/bin/python /app/backup.py`. Debian `python3` does not have the image's libraries. If a start command is required, set exactly:
   ```text
   /opt/venv/bin/python /app/backup.py
   ```
4. **Settings → Cron Schedule:** `30 7 * * *`
   That is 07:30 UTC every day. Railway evaluates cron in UTC, and runs must be at least 5 minutes apart. This schedule is daily.
5. Do not attach a public domain. Do not set a healthcheck path. A healthcheck expects a server that stays up; this process must exit.
6. Set **Restart Policy** to **Never**. The script already emails on failure. A restart loop would send that email again and can leave the previous run `Active`, which makes Railway skip the next scheduled run.
7. Do not attach a volume. The dump is uploaded and then deleted from the container disk.
8. Add the variables in the next section, then deploy the service once so the image builds.
9. Trigger one run outside the schedule, with the CLI linked to `postgres-backup` and not to the API service:
   ```bash
   railway link
   railway cron run
   ```
   `railway cron list` shows recent runs. A successful run exits 0 and prints `backup complete key=...`. The bucket then has an object under `supabase/` whose name starts with `agentnexlify-` and ends in `.dump.enc` or `.dump.age`.

The container uses the Postgres 17 client, which can dump Postgres 15 and 17. If Supabase moves to a newer major version, bump the `FROM` line in `ops/db-backup/Dockerfile` before the next dump.

## Database URL

Railway's egress is IPv4. On the Free plan the direct host `db.pxserpybmajixqrmzaly.supabase.co` is IPv6-only, so use the **session pooler** URI (port **5432**).

In the Supabase dashboard open the project, choose **Connect**, and copy the **Session pooler** URI. It looks like:

```text
postgresql://postgres.pxserpybmajixqrmzaly:[PASSWORD]@aws-0-[region].pooler.supabase.com:5432/postgres
```

URL-encode reserved characters in the password (`@` becomes `%40`). Append `?sslmode=require` when the URI does not already set `sslmode`.

Do not use port **6543** and do not use a URI with `pgbouncer=true`. That is the transaction pooler, and `pg_dump` fails against it. Do not reuse the API service's `DATABASE_URL` when that value is the transaction pooler. Set `BACKUP_DATABASE_URL` on `postgres-backup` only.

A direct `db.<ref>.supabase.co:5432` URI is accepted when the host is reachable over IPv4. The session pooler is the Free-plan setting that works from Railway.

## Environment variables

Set these on the Railway service `postgres-backup`. Do not put the age private key on Railway.

### Required

| Variable | Value |
|---|---|
| `BACKUP_DATABASE_URL` | Session-pooler or direct Postgres URI, port 5432, `sslmode=require`. Used instead of `DATABASE_URL` when both are set. |
| `BACKUP_S3_ENDPOINT_URL` | R2: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`. B2: `https://s3.<region>.backblazeb2.com`. https only, no credentials in the URL. |
| `BACKUP_S3_BUCKET` | Bucket name, for example `agentnexlify-backups`. |
| `BACKUP_S3_ACCESS_KEY_ID` | R2 access key id, or the B2 application key id. |
| `BACKUP_S3_SECRET_ACCESS_KEY` | R2 secret, or the B2 application key. |
| `RESEND_API_KEY` | Resend API key with permission to send. The same key the backend uses is fine. |
| `BACKUP_ALERT_EMAIL` | Inbox that receives failure mail. `OWNER_ALERT_EMAIL` is used only when `BACKUP_ALERT_EMAIL` is unset. |

### Optional

| Variable | Default | Value |
|---|---|---|
| `BACKUP_S3_REGION` | `auto` | Use `auto` for R2. For B2, set the region id in the endpoint, for example `us-west-004`. |
| `BACKUP_S3_PREFIX` | `supabase/` | Key prefix. A missing trailing slash is added. `..` and a leading slash are rejected. |
| `BACKUP_S3_ADDRESSING_STYLE` | `path` | `path` or `virtual`. `path` works for R2 and B2. |
| `ALERT_FROM_ADDRESS` | `AgentNexLiFy Alerts <noreply@agentnexlify.com>` | Resend From header. The address must be on a verified domain. |

### Required: one encryption key

Set `BACKUP_AGE_RECIPIENT` (age public key, `age1...`). That is the key to use. If it is unset, set `BACKUP_ENCRYPTION_KEY` (AES-256-GCM passphrase, also stored in the password manager). When both are set, age is used and the passphrase is ignored. When neither is set, the job exits before `pg_dump`.
| `DATABASE_URL` | unset | Fallback only when `BACKUP_DATABASE_URL` is empty. Same port rules. |

### Not set on Railway

| Name | Where it lives |
|---|---|
| age identity file (`age-keygen` output) | Password manager and the restore workstation. Passed to `restore.py --age-identity`. Never upload it to Railway, GitHub, or the bucket. |
| `BACKUP_ALLOW_REMOTE_RESTORE=yes` | Restore workstation only, and only when the target is a scratch Supabase project. The script still refuses project `pxserpybmajixqrmzaly`. |

One of `BACKUP_AGE_RECIPIENT` or `BACKUP_ENCRYPTION_KEY` is required. The job refuses to start when both are empty, and it never uploads a plaintext `.dump`.

## Retention and the bucket credential

The cron process only calls `PutObject`. It does not call `DeleteObject` or `ListObjects`. Expire old archives with a lifecycle rule on the `supabase/` prefix. Use 21 days. Any value from 14 through 30 is acceptable. Do not attach a rule that expires the whole bucket with no prefix.

The backup credential must not be allowed to delete objects. Lifecycle expiration is performed by the storage provider, not by this key.

### Cloudflare R2

1. Open the bucket → **Settings** → **Object lifecycle rules** → **Add rule**.
2. Prefix: `supabase/`. Action: expire objects after 21 days.
3. Create an API token that can `s3:PutObject`, `s3:CreateMultipartUpload`, `s3:UploadPart`, `s3:CompleteMultipartUpload`, and `s3:AbortMultipartUpload` on this bucket. Omit `s3:DeleteObject`. Do not use the **Admin Read & Write** preset; that preset can delete. A separate restore token may also have `s3:GetObject` and `s3:ListBucket`.
4. Optional: enable Object Lock so a newly uploaded object cannot be removed before its retention date. The lifecycle rule still expires it when the rule says so.

### Backblaze B2

1. Bucket → **Lifecycle Settings**. Prefix `supabase/`. `daysFromUploadingToHiding` and `daysFromHidingToDeleting` should add up to the retention you want, with the uploaded file gone after 21 days. A simple setting is hide after 21 days and delete 1 day after hiding.
2. Application key capabilities: `listBuckets`, `writeFiles`. Leave `deleteFiles` unchecked. A restore key may add `listFiles` and `readFiles`. Restrict the key to this bucket.

Turn on the bucket's own server-side encryption if the provider offers it. That is in addition to age or AES-GCM.

Generate an age key on a workstation (this is the option to use):

```bash
age-keygen -o backup-age.key
chmod 600 backup-age.key
```

The comment line `# public key: age1...` is `BACKUP_AGE_RECIPIENT`. Keep `backup-age.key` offline.

A table lock held longer than 60 seconds fails the dump, sends the alert, and leaves the previous object in place.

## Failure email

Resend receives one message per failed process:

- Subject: `[AgentNexLiFy] Postgres backup failed`
- Body: UTC time and the error, with database URLs and known secrets redacted
- The script then exits 1

If `RESEND_API_KEY` or the alert address is missing, the process still exits 1 and prints that the email was not sent. Railway logs are the signal in that case.

To confirm the mail path without dumping production, this is not automated here. After the service exists, a bad `BACKUP_S3_BUCKET` on one manual `railway cron run` produces the email. Set the bucket back before the next 07:30 UTC run.

## Restore

Restore into local Postgres or into a new scratch Supabase project. The restore command refuses:

- any URL whose user or host contains `pxserpybmajixqrmzaly`
- a target that is the same host, port, and database as `BACKUP_DATABASE_URL` or `DATABASE_URL` in the environment
- any other Supabase host unless `BACKUP_ALLOW_REMOTE_RESTORE=yes`

Unset `BACKUP_DATABASE_URL` and `DATABASE_URL` in the shell you restore from.

Install client tools and Python dependencies on the workstation:

```bash
python3 -m venv .venv-backup
.venv-backup/bin/pip install -r ops/db-backup/requirements.txt
```

`pg_restore` must be on `PATH` (Postgres client 15 or newer; 17 matches the backup image).

### 1. Download

```bash
export BACKUP_S3_ENDPOINT_URL='https://<ACCOUNT_ID>.r2.cloudflarestorage.com'
export BACKUP_S3_BUCKET='agentnexlify-backups'
export BACKUP_S3_ACCESS_KEY_ID='...'
export BACKUP_S3_SECRET_ACCESS_KEY='...'
export BACKUP_S3_REGION='auto'
export BACKUP_S3_ADDRESSING_STYLE='path'
```

```bash
.venv-backup/bin/python ops/db-backup/restore.py \
  --input 's3://agentnexlify-backups/supabase/agentnexlify-YYYYMMDDTHHMMSSZ.dump.age' \
  --target-url 'postgresql://postgres@127.0.0.1:5432/restore_drill' \
  --age-identity /path/to/backup-age.key \
  --schema public
```

Create the empty database first: `createdb restore_drill`. `restore.py` passes the database password to `pg_restore` through libpq's environment, not on the process command line.

For a `.dump.enc` object, pass `--encryption-key "$BACKUP_ENCRYPTION_KEY"` and omit `--age-identity`. A plaintext `.dump` is refused.

`--schema public` is the right check for a production archive. A full restore into vanilla Postgres fails on Supabase-only extensions (`supabase_vault`, `pg_net`, and the rest). The archive itself is still a full database dump.

### 2. What the local test already proved

`tests/test_postgres_offsite_restore.py` starts Postgres on `127.0.0.1`, writes two rows (including `café`), dumps with the same `pg_dump` flags the cron uses, and restores AES-GCM (`.dump.enc`) and age (`.dump.age`). It checks both rows after each restore. `tests/test_postgres_offsite_backup.py` checks that a plaintext `.dump` is refused and that a target containing `pxserpybmajixqrmzaly` is refused before any socket or `pg_restore` call.

PR Validation runs `pytest tests`, which collects both files. The workflow installs PostgreSQL and `age` first. Do not point the test at a Supabase URL.

```bash
python3 -m pytest tests/test_postgres_offsite_backup.py tests/test_postgres_offsite_restore.py -q
```

### 3. Confirm a production archive

After a real dump exists, restore `--schema public` into local Postgres and compare counts with production (read-only):

```sql
SELECT
  (SELECT count(*) FROM tenants)       AS tenants,
  (SELECT count(*) FROM leads)         AS leads,
  (SELECT count(*) FROM chat_messages) AS chat_messages;
```

### 4. Scratch Supabase project

Only for a real recovery rehearsal or an actual outage. Create a new project. Do not use `pxserpybmajixqrmzaly`.

```bash
export BACKUP_ALLOW_REMOTE_RESTORE=yes
.venv-backup/bin/python ops/db-backup/restore.py \
  --input 's3://agentnexlify-backups/supabase/agentnexlify-YYYYMMDDTHHMMSSZ.dump.age' \
  --target-url 'postgresql://postgres.<SCRATCH_REF>:[PASSWORD]@aws-0-[region].pooler.supabase.com:5432/postgres?sslmode=require' \
  --age-identity /path/to/backup-age.key \
  --schema public
```

Use the scratch project's session-pooler URI on port 5432. Delete the scratch project when the check is done. `auth.users` lives in the `auth` schema, not `public`. Restoring `auth` into a Supabase project that already has that schema conflicts; do that only on the scratch project, during a real recovery.

### ANX1 passphrase format

A `.dump.enc` file is, in order: magic `ANX1` (4 bytes), salt (16), nonce (12), ciphertext, GCM tag (16). The key is PBKDF2-HMAC-SHA256, 200,000 iterations, 32 bytes. The cipher is AES-256-GCM. `restore.py` is the supported decryptor. A wrong passphrase fails the tag check and does not call `pg_restore`.

A `.dump.age` file is a standard age ciphertext for the public key stored in `BACKUP_AGE_RECIPIENT`. Decrypt it with the identity file from `age-keygen`.

## What this does not do

- It is not point-in-time recovery. The newest restorable copy is the last successful cron run.
- It does not back up Supabase Storage objects, only the Postgres cluster `pg_dump` can see.
- It does not run until the Railway service above exists and the variables are set.
