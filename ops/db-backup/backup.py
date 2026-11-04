"""Nightly off-site backup of the Supabase Postgres database.

Railway runs this as its own cron service (root directory ops/db-backup).
It dumps with pg_dump custom format at gzip level 6, encrypts with age
(preferred) or AES-256-GCM, and uploads to R2 or B2. A missing encryption
key is a hard failure. The job never deletes objects; retention is a
bucket lifecycle rule. A failure sends one Resend email and exits non-zero.

pg_dump is read-only. This file does not apply migrations or write to the
source database. Nothing here talks to Railway or Supabase until an
operator sets the service variables and the cron runs.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

from backup_common import (
    AGE_RECIPIENT_RE,
    ConfigError,
    DatabaseTarget,
    backup_object_name,
    encrypt_backup_file,
    normalize_prefix,
    parse_database_url,
    redact,
    require_encryption,
    run_pg_dump,
    sha256_file,
)

DEFAULT_FROM = "AgentNexLiFy Alerts <noreply@agentnexlify.com>"
RESEND_URL = "https://api.resend.com/emails"


class BackupStore(Protocol):
    def upload(self, key: str, path: Path) -> None: ...


@dataclass(frozen=True)
class S3Settings:
    endpoint_url: str
    bucket: str
    region: str
    addressing_style: str
    access_key_id: str = field(repr=False)
    secret_access_key: str = field(repr=False)


@dataclass(frozen=True)
class BackupConfig:
    target: DatabaseTarget
    database_url_var: str
    s3: S3Settings
    prefix: str
    age_recipient: str
    alert_email: str
    alert_from: str
    encryption_key: str = field(repr=False)
    resend_api_key: str = field(repr=False)

    @property
    def endpoint_url(self) -> str:
        return self.s3.endpoint_url

    @property
    def bucket(self) -> str:
        return self.s3.bucket


@dataclass(frozen=True)
class BackupResult:
    key: str
    byte_count: int
    sha256: str
    encryption: str


def _present(name: str) -> str:
    return os.environ.get(name, "").strip()


def s3_settings_from_env() -> S3Settings:
    endpoint = _present("BACKUP_S3_ENDPOINT_URL")
    bucket = _present("BACKUP_S3_BUCKET")
    access_key_id = _present("BACKUP_S3_ACCESS_KEY_ID")
    secret_access_key = _present("BACKUP_S3_SECRET_ACCESS_KEY")
    missing = [
        name
        for name, value in (
            ("BACKUP_S3_ENDPOINT_URL", endpoint),
            ("BACKUP_S3_BUCKET", bucket),
            ("BACKUP_S3_ACCESS_KEY_ID", access_key_id),
            ("BACKUP_S3_SECRET_ACCESS_KEY", secret_access_key),
        )
        if not value
    ]
    if missing:
        raise ConfigError("Missing required environment: " + ", ".join(missing))
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ConfigError(
            "BACKUP_S3_ENDPOINT_URL must be an https URL with no embedded credentials"
        )
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,61}[A-Za-z0-9]", bucket):
        raise ConfigError("BACKUP_S3_BUCKET must be a bucket name")
    region = _present("BACKUP_S3_REGION") or "auto"
    if not re.fullmatch(r"[A-Za-z0-9_-]+", region):
        raise ConfigError("BACKUP_S3_REGION contains unsupported characters")
    style = _present("BACKUP_S3_ADDRESSING_STYLE") or "path"
    if style not in {"path", "virtual"}:
        raise ConfigError("BACKUP_S3_ADDRESSING_STYLE must be path or virtual")
    return S3Settings(
        endpoint_url=endpoint,
        bucket=bucket,
        region=region,
        addressing_style=style,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
    )


def load_config() -> BackupConfig:
    backup_url = _present("BACKUP_DATABASE_URL")
    database_url = backup_url or _present("DATABASE_URL")
    resend_api_key = _present("RESEND_API_KEY")
    alert_email = _present("BACKUP_ALERT_EMAIL") or _present("OWNER_ALERT_EMAIL")
    missing = []
    if not database_url:
        missing.append("BACKUP_DATABASE_URL (or DATABASE_URL)")
    if not resend_api_key:
        missing.append("RESEND_API_KEY")
    if not alert_email:
        missing.append("BACKUP_ALERT_EMAIL (or OWNER_ALERT_EMAIL)")
    if missing:
        raise ConfigError("Missing required environment: " + ", ".join(missing))
    if "@" not in alert_email or alert_email.startswith("@") or alert_email.endswith("@"):
        raise ConfigError("BACKUP_ALERT_EMAIL must be an email address")
    alert_from = _present("ALERT_FROM_ADDRESS") or DEFAULT_FROM
    if "@" not in alert_from:
        raise ConfigError("ALERT_FROM_ADDRESS must include an email address")
    age_recipient = _present("BACKUP_AGE_RECIPIENT")
    if age_recipient and not AGE_RECIPIENT_RE.fullmatch(age_recipient):
        raise ConfigError("BACKUP_AGE_RECIPIENT must be an age public key (age1...)")
    if age_recipient and shutil.which("age") is None:
        raise ConfigError("BACKUP_AGE_RECIPIENT is set but the age binary is not installed")
    encryption_key = _present("BACKUP_ENCRYPTION_KEY")
    require_encryption(age_recipient, encryption_key)
    return BackupConfig(
        target=parse_database_url(database_url),
        database_url_var="BACKUP_DATABASE_URL" if backup_url else "DATABASE_URL",
        s3=s3_settings_from_env(),
        prefix=normalize_prefix(os.environ.get("BACKUP_S3_PREFIX")),
        age_recipient=age_recipient,
        encryption_key=encryption_key,
        alert_email=alert_email,
        alert_from=alert_from,
        resend_api_key=resend_api_key,
    )


def make_s3_client(settings: S3Settings):
    import boto3
    from botocore.config import Config

    base = {
        "signature_version": "s3v4",
        "s3": {"addressing_style": settings.addressing_style},
    }
    try:
        config = Config(
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
            **base,
        )
    except TypeError:
        config = Config(**base)
    return boto3.client(
        "s3",
        endpoint_url=settings.endpoint_url,
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key,
        region_name=settings.region,
        config=config,
    )


class S3BackupStore:
    def __init__(self, client, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    def upload(self, key: str, path: Path) -> None:
        self.client.upload_file(
            str(path),
            self.bucket,
            key,
            ExtraArgs={"ContentType": "application/octet-stream"},
        )


def send_failure_alert(detail: str, *, api_key: str, to_email: str, from_address: str) -> None:
    safe_detail = redact(detail)[-4000:]
    payload = {
        "from": from_address,
        "to": [to_email],
        "subject": "[AgentNexLiFy] Postgres backup failed",
        "text": (
            "The nightly Supabase Postgres backup did not finish.\n\n"
            f"Time (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
            f"Error: {safe_detail}\n\n"
            "Railway service: postgres-backup\n"
            "Previous off-site backups were left in place.\n"
        ),
    }
    request = urllib.request.Request(
        RESEND_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "agentnexlify-postgres-backup",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = getattr(response, "status", 200)
            if status < 200 or status >= 300:
                raise RuntimeError(f"Resend returned HTTP {status}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Resend returned HTTP {exc.code}") from None


def run_backup(
    cfg: BackupConfig,
    *,
    store: BackupStore | None = None,
    now: datetime | None = None,
    pg_dump_bin: str = "pg_dump",
) -> BackupResult:
    moment = now or datetime.now(timezone.utc)
    if store is None:
        store = S3BackupStore(make_s3_client(cfg.s3), cfg.bucket)
    mode = require_encryption(cfg.age_recipient, cfg.encryption_key)
    if cfg.age_recipient and cfg.encryption_key:
        print("BACKUP_AGE_RECIPIENT is set, so BACKUP_ENCRYPTION_KEY is not used", flush=True)
    try:
        version = subprocess.run(
            [pg_dump_bin, "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise RuntimeError(f"pg_dump is not installed: {exc}") from None
    if version.returncode != 0:
        detail = redact((version.stderr or "pg_dump --version failed").strip())
        raise RuntimeError(detail)
    if version.stdout.strip():
        print(version.stdout.strip(), flush=True)
    print(
        f"database_url_var={cfg.database_url_var} encryption={mode}",
        flush=True,
    )
    work = Path(tempfile.mkdtemp(prefix="anx-backup-"))
    os.chmod(work, 0o700)
    try:
        plain = work / "backup.dump"
        run_pg_dump(cfg.target, plain, pg_dump_bin=pg_dump_bin)
        payload, used_mode = encrypt_backup_file(
            plain,
            age_recipient=cfg.age_recipient,
            encryption_key=cfg.encryption_key,
        )
        key = cfg.prefix + backup_object_name(moment, used_mode)
        store.upload(key, payload)
        return BackupResult(
            key=key,
            byte_count=payload.stat().st_size,
            sha256=sha256_file(payload),
            encryption=used_mode,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _alert_targets(cfg: BackupConfig | None) -> tuple[str, str, str]:
    if cfg is not None:
        return cfg.resend_api_key, cfg.alert_email, cfg.alert_from
    return (
        _present("RESEND_API_KEY"),
        _present("BACKUP_ALERT_EMAIL") or _present("OWNER_ALERT_EMAIL"),
        _present("ALERT_FROM_ADDRESS") or DEFAULT_FROM,
    )


def main() -> int:
    os.umask(0o077)
    cfg = None
    try:
        cfg = load_config()
        result = run_backup(cfg)
    except Exception as exc:
        detail = redact(f"{type(exc).__name__}: {exc}")
        print(f"backup failed: {detail}", file=sys.stderr)
        api_key, to_email, from_address = _alert_targets(cfg)
        if api_key and to_email:
            try:
                send_failure_alert(
                    detail,
                    api_key=api_key,
                    to_email=to_email,
                    from_address=from_address,
                )
                print("failure alert emailed", file=sys.stderr)
            except Exception as alert_exc:
                print(
                    f"failure alert also failed: {redact(str(alert_exc))}",
                    file=sys.stderr,
                )
        else:
            print(
                "failure alert not sent: RESEND_API_KEY or BACKUP_ALERT_EMAIL is missing",
                file=sys.stderr,
            )
        return 1
    print(
        "backup complete "
        f"key={result.key} bytes={result.byte_count} sha256={result.sha256} "
        f"encryption={result.encryption}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
