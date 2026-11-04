"""Shared dump, encryption, and retention helpers for the off-site backup.

The Railway cron entrypoint is backup.py. Restore uses the same URL parser,
AES-GCM format, and age commands so a backup written at night can be read back
on a workstation.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


MAGIC = b"ANX1"
SALT_LEN = 16
NONCE_LEN = 12
TAG_LEN = 16
KDF_ITERATIONS = 200_000
CHUNK = 1024 * 1024
PRODUCTION_PROJECT_REF = "pxserpybmajixqrmzaly"
AGE_RECIPIENT_RE = re.compile(r"age1[0-9a-z]{20,}")


class ConfigError(Exception):
    """The job cannot start, or a restore was refused, because the inputs are wrong."""


@dataclass(frozen=True)
class DatabaseTarget:
    host: str
    port: int
    user: str
    dbname: str
    sslmode: str | None
    pgbouncer: bool
    password: str = field(repr=False, default="")


def redact(text: str, extra: tuple[str, ...] = ()) -> str:
    """Strip connection strings and known secrets before they reach logs or email."""
    if not text:
        return ""
    cleaned = re.sub(r"postgres(?:ql)?://\S+", "postgresql://REDACTED", text)
    cleaned = re.sub(r"://[^/\s:]+:[^@\s/]+@", "://REDACTED@", cleaned)
    cleaned = re.sub(r"(X-Amz-Signature=)[^&\s]+", r"\1REDACTED", cleaned)
    cleaned = re.sub(r"(X-Amz-Credential=)[^&\s]+", r"\1REDACTED", cleaned)
    secrets = list(extra)
    for name in (
        "PGPASSWORD",
        "BACKUP_ENCRYPTION_KEY",
        "BACKUP_S3_SECRET_ACCESS_KEY",
        "BACKUP_S3_ACCESS_KEY_ID",
        "RESEND_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_ACCESS_KEY_ID",
    ):
        value = os.environ.get(name, "")
        if value:
            secrets.append(value)
    for value in secrets:
        if len(value) >= 6:
            cleaned = cleaned.replace(value, "REDACTED")
    return cleaned


def parse_database_url(url: str, *, allow_pooler: bool = False) -> DatabaseTarget:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ConfigError(
            "Database URL must start with postgresql://. "
            "URL-encode reserved characters in the password."
        )
    if not parsed.hostname or not parsed.username:
        raise ConfigError(
            "Database URL is missing a host or user. "
            "URL-encode reserved characters in the password."
        )
    query = parse_qs(parsed.query, keep_blank_values=True)
    pgbouncer = any(item.lower() == "true" for item in query.get("pgbouncer", []))
    port = parsed.port or 5432
    if (port == 6543 or pgbouncer) and not allow_pooler:
        raise ConfigError(
            "Database URL uses the Supabase transaction pooler (port 6543 or "
            "pgbouncer=true). pg_dump and pg_restore need the direct connection "
            "or the session pooler, both on port 5432."
        )
    dbname = unquote(parsed.path.lstrip("/")) or "postgres"
    sslmode_values = query.get("sslmode", [])
    sslmode = sslmode_values[0] if sslmode_values else None
    return DatabaseTarget(
        host=parsed.hostname,
        port=port,
        user=unquote(parsed.username),
        password=unquote(parsed.password or ""),
        dbname=dbname,
        sslmode=sslmode,
        pgbouncer=pgbouncer,
    )


def libpq_env(target: DatabaseTarget, *, app_name: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PGHOST"] = target.host
    env["PGPORT"] = str(target.port)
    env["PGUSER"] = target.user
    env["PGDATABASE"] = target.dbname
    env["PGAPPNAME"] = app_name
    env["PGCONNECT_TIMEOUT"] = "20"
    if target.password:
        env["PGPASSWORD"] = target.password
    else:
        env.pop("PGPASSWORD", None)
    if target.sslmode:
        env["PGSSLMODE"] = target.sslmode
    elif target.host in {"localhost", "127.0.0.1", "::1"}:
        env.pop("PGSSLMODE", None)
    else:
        env["PGSSLMODE"] = "require"
    return env


def _run_pg_tool(cmd: list[str], env: dict[str, str], password: str, failure: str) -> None:
    completed = subprocess.run(cmd, env=env, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        detail = redact((completed.stderr or completed.stdout or failure).strip(), extra=(password,))
        raise RuntimeError(f"{failure}: {detail[-4000:]}")


def run_pg_dump(target: DatabaseTarget, output: Path, pg_dump_bin: str = "pg_dump") -> None:
    env = libpq_env(target, app_name="agentnexlify-backup")
    cmd = [
        pg_dump_bin,
        "--format=custom",
        "-Z",
        "6",
        "--no-owner",
        "--no-privileges",
        "--lock-wait-timeout=60s",
        "--file",
        str(output),
    ]
    _run_pg_tool(cmd, env, target.password, "pg_dump failed")
    with output.open("rb") as handle:
        header = handle.read(5)
    if header != b"PGDMP":
        raise RuntimeError("pg_dump did not write a custom-format archive")
    os.chmod(output, 0o600)


def run_pg_restore(
    target: DatabaseTarget,
    archive: Path,
    schemas: list[str],
    pg_restore_bin: str = "pg_restore",
) -> None:
    for schema in schemas:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", schema):
            raise ConfigError(f"Invalid schema name: {schema}")
    env = libpq_env(target, app_name="agentnexlify-restore")
    cmd = [
        pg_restore_bin,
        "--no-owner",
        "--no-privileges",
        "--exit-on-error",
        "--dbname",
        target.dbname,
    ]
    for schema in schemas:
        cmd.extend(["--schema", schema])
    cmd.append(str(archive))
    _run_pg_tool(cmd, env, target.password, "pg_restore failed")


def normalize_prefix(raw: str | None) -> str:
    if raw is None or raw.strip() == "":
        return "supabase/"
    prefix = raw.strip()
    if not prefix.endswith("/"):
        prefix += "/"
    parts = prefix.split("/")
    if prefix.startswith("/") or any(part == ".." for part in parts):
        raise ConfigError("BACKUP_S3_PREFIX must be a relative key prefix")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", prefix):
        raise ConfigError("BACKUP_S3_PREFIX contains unsupported characters")
    return prefix


def _as_utc(now: datetime) -> datetime:
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def backup_object_name(now: datetime, mode: str) -> str:
    stamp = _as_utc(now).strftime("%Y%m%dT%H%M%SZ")
    suffix = {"aes-gcm": ".enc", "age": ".age"}[mode]
    return f"agentnexlify-{stamp}.dump{suffix}"


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_aes_file(src: Path, dst: Path, passphrase: str) -> None:
    """Write ANX1 || salt(16) || nonce(12) || ciphertext || tag(16).

    The key is PBKDF2-HMAC-SHA256, 200_000 iterations, 32 bytes. The cipher is
    AES-256-GCM. A wrong passphrase fails closed on the tag.
    """
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    encryptor = Cipher(algorithms.AES(_derive_key(passphrase, salt)), modes.GCM(nonce)).encryptor()
    try:
        with src.open("rb") as source, dst.open("wb") as target:
            target.write(MAGIC + salt + nonce)
            while True:
                chunk = source.read(CHUNK)
                if not chunk:
                    break
                target.write(encryptor.update(chunk))
            target.write(encryptor.finalize())
            target.write(encryptor.tag)
        os.chmod(dst, 0o600)
    except Exception:
        dst.unlink(missing_ok=True)
        raise


def decrypt_aes_file(src: Path, dst: Path, passphrase: str) -> None:
    size = src.stat().st_size
    header_len = len(MAGIC) + SALT_LEN + NONCE_LEN
    if size < header_len + TAG_LEN + 1:
        raise ConfigError("Encrypted backup is too small to be an ANX1 archive")
    with src.open("rb") as source:
        magic = source.read(len(MAGIC))
        if magic != MAGIC:
            raise ConfigError("Backup is not an ANX1 encrypted archive")
        salt = source.read(SALT_LEN)
        nonce = source.read(NONCE_LEN)
        source.seek(size - TAG_LEN)
        tag = source.read(TAG_LEN)
        decryptor = Cipher(
            algorithms.AES(_derive_key(passphrase, salt)),
            modes.GCM(nonce, tag),
        ).decryptor()
        source.seek(header_len)
        remaining = size - header_len - TAG_LEN
        try:
            with dst.open("wb") as target:
                while remaining:
                    chunk = source.read(min(CHUNK, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    target.write(decryptor.update(chunk))
                target.write(decryptor.finalize())
            os.chmod(dst, 0o600)
        except InvalidTag:
            dst.unlink(missing_ok=True)
            raise ConfigError(
                "Decryption failed. BACKUP_ENCRYPTION_KEY does not match this archive."
            ) from None
        except Exception:
            dst.unlink(missing_ok=True)
            raise


def run_age_encrypt(src: Path, dst: Path, recipient: str) -> None:
    if not AGE_RECIPIENT_RE.fullmatch(recipient):
        raise ConfigError("BACKUP_AGE_RECIPIENT must be an age public key (age1...)")
    completed = subprocess.run(
        ["age", "-r", recipient, "-o", str(dst), str(src)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        dst.unlink(missing_ok=True)
        detail = (completed.stderr or completed.stdout or "age failed").strip()
        raise RuntimeError(f"age encryption failed: {redact(detail)[-2000:]}")
    os.chmod(dst, 0o600)


def run_age_decrypt(src: Path, dst: Path, identity: Path) -> None:
    if not identity.is_file():
        raise ConfigError(f"age identity file not found: {identity}")
    mode = identity.stat().st_mode & 0o077
    if mode:
        print(
            f"warning: {identity} is readable by someone other than the owner; chmod 600 it",
            flush=True,
        )
    completed = subprocess.run(
        ["age", "-d", "-i", str(identity), "-o", str(dst), str(src)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        dst.unlink(missing_ok=True)
        detail = (completed.stderr or completed.stdout or "age failed").strip()
        raise RuntimeError(f"age decryption failed: {redact(detail)[-2000:]}")
    os.chmod(dst, 0o600)


def require_encryption(age_recipient: str, encryption_key: str) -> str:
    """Age is preferred. A missing key is a hard stop, not a plaintext upload."""
    if age_recipient:
        return "age"
    if encryption_key:
        return "aes-gcm"
    raise ConfigError(
        "Refusing to run without encryption. Set BACKUP_AGE_RECIPIENT "
        "(preferred) or BACKUP_ENCRYPTION_KEY."
    )


def encrypt_backup_file(src: Path, *, age_recipient: str, encryption_key: str) -> tuple[Path, str]:
    mode = require_encryption(age_recipient, encryption_key)
    suffix = ".age" if mode == "age" else ".enc"
    dst = src.with_name(src.name + suffix)
    if mode == "age":
        run_age_encrypt(src, dst, age_recipient)
    else:
        encrypt_aes_file(src, dst, encryption_key)
    src.unlink()
    return dst, mode


def encryption_kind(path: Path) -> str:
    name = path.name
    if name.endswith(".dump.age"):
        return "age"
    if name.endswith(".dump.enc"):
        return "aes-gcm"
    raise ConfigError(
        "Backup filename must end in .dump.enc or .dump.age. "
        "Plaintext .dump archives are not restored."
    )


def assert_custom_dump(path: Path) -> None:
    with path.open("rb") as handle:
        header = handle.read(5)
    if header != b"PGDMP":
        raise ConfigError("Archive is not a PostgreSQL custom-format dump")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_restore_target_allowed(target: DatabaseTarget) -> None:
    identity = f"{target.user}@{target.host}"
    if PRODUCTION_PROJECT_REF in identity:
        raise ConfigError(
            "Refusing to restore into production Supabase project "
            f"{PRODUCTION_PROJECT_REF}. Use a local Postgres or a new scratch project."
        )
    source_raw = (
        os.environ.get("BACKUP_DATABASE_URL", "").strip()
        or os.environ.get("DATABASE_URL", "").strip()
    )
    if source_raw:
        try:
            source = parse_database_url(source_raw, allow_pooler=True)
        except ConfigError:
            source = None
        if source and (source.host, source.port, source.dbname) == (
            target.host,
            target.port,
            target.dbname,
        ):
            raise ConfigError("Refusing to restore into the source database.")
    host = target.host.lower()
    remote = host.endswith(".supabase.co") or "pooler.supabase.com" in host
    if remote and os.environ.get("BACKUP_ALLOW_REMOTE_RESTORE") != "yes":
        raise ConfigError(
            "Refusing to restore into a Supabase host. Restore into local Postgres, "
            "or set BACKUP_ALLOW_REMOTE_RESTORE=yes only when the target is a scratch project."
        )


def require_dumpable(target: DatabaseTarget) -> None:
    if target.port == 6543 or target.pgbouncer:
        raise ConfigError(
            "Database URL uses the Supabase transaction pooler (port 6543 or "
            "pgbouncer=true). pg_dump and pg_restore need the direct connection "
            "or the session pooler, both on port 5432."
        )
