"""Restore a backup produced by backup.py into a target Postgres database.

The target must be a local Postgres or, with BACKUP_ALLOW_REMOTE_RESTORE=yes,
a scratch Supabase project. The production project ref is always refused.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from backup_common import (
    ConfigError,
    assert_custom_dump,
    assert_restore_target_allowed,
    decrypt_aes_file,
    encryption_kind,
    parse_database_url,
    redact,
    require_dumpable,
    run_age_decrypt,
    run_pg_restore,
)


def _download_s3(url: str, dest: Path) -> None:
    parsed = urlparse(url)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    if parsed.scheme != "s3" or not bucket or not key or key.endswith("/"):
        raise ConfigError("S3 input must look like s3://bucket/key")
    from backup import make_s3_client, s3_settings_from_env

    settings = s3_settings_from_env()
    if bucket != settings.bucket:
        raise ConfigError("S3 URL bucket does not match BACKUP_S3_BUCKET")
    make_s3_client(settings).download_file(bucket, key, str(dest))
    os.chmod(dest, 0o600)


def _materialize(source: str, work: Path) -> Path:
    if source.startswith("s3://"):
        suffixes = "".join(Path(urlparse(source).path).suffixes)
        if not suffixes:
            raise ConfigError("S3 object name must end in .dump, .dump.enc, or .dump.age")
        dest = work / f"download{suffixes}"
        _download_s3(source, dest)
        return dest
    path = Path(source)
    if not path.is_file():
        raise ConfigError(f"Backup file not found: {path}")
    return path


def perform_restore(
    *,
    source: str,
    target_url: str,
    encryption_key: str,
    age_identity: str,
    schemas: list[str],
) -> None:
    target = parse_database_url(target_url, allow_pooler=True)
    assert_restore_target_allowed(target)
    require_dumpable(target)
    passphrase = encryption_key or os.environ.get("BACKUP_ENCRYPTION_KEY", "").strip()
    work = Path(tempfile.mkdtemp(prefix="anx-restore-"))
    os.chmod(work, 0o700)
    try:
        stored = _materialize(source, work)
        kind = encryption_kind(stored)
        if kind == "none":
            archive = stored
        elif kind == "aes-gcm":
            if not passphrase:
                raise ConfigError("This archive needs --encryption-key or BACKUP_ENCRYPTION_KEY")
            archive = work / "restore.dump"
            decrypt_aes_file(stored, archive, passphrase)
        else:
            if not age_identity:
                raise ConfigError("This archive needs --age-identity")
            archive = work / "restore.dump"
            run_age_decrypt(stored, archive, Path(age_identity))
        assert_custom_dump(archive)
        run_pg_restore(target, archive, schemas)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    os.umask(0o077)
    parser = argparse.ArgumentParser(
        description="Restore an AgentNexLiFy Postgres backup into a target database."
    )
    parser.add_argument("--input", required=True, help="Local path or s3://bucket/key")
    parser.add_argument("--target-url", required=True, help="Postgres URI to restore into")
    parser.add_argument("--encryption-key", default="", help="Passphrase for a .dump.enc archive")
    parser.add_argument("--age-identity", default="", help="Path to the age private key")
    parser.add_argument(
        "--schema",
        action="append",
        default=[],
        help="Restore only this schema. Repeat for more than one. Example: --schema public",
    )
    args = parser.parse_args(argv)
    try:
        perform_restore(
            source=args.input,
            target_url=args.target_url,
            encryption_key=args.encryption_key,
            age_identity=args.age_identity,
            schemas=args.schema,
        )
    except Exception as exc:
        print(f"restore failed: {redact(str(exc))}", file=sys.stderr)
        return 1
    print("restore complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
