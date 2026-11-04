"""Unit tests for the off-site backup. No network and no production database."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

import backup
import backup_common
from backup_common import ConfigError

NOW = datetime(2026, 11, 4, 7, 30, tzinfo=timezone.utc)
PREFIX = "supabase/"


def apply_env(monkeypatch, **overrides):
    names = [
        "BACKUP_DATABASE_URL",
        "DATABASE_URL",
        "BACKUP_S3_ENDPOINT_URL",
        "BACKUP_S3_BUCKET",
        "BACKUP_S3_ACCESS_KEY_ID",
        "BACKUP_S3_SECRET_ACCESS_KEY",
        "BACKUP_S3_REGION",
        "BACKUP_S3_PREFIX",
        "BACKUP_S3_ADDRESSING_STYLE",
        "BACKUP_RETENTION_DAYS",
        "BACKUP_AGE_RECIPIENT",
        "BACKUP_ENCRYPTION_KEY",
        "RESEND_API_KEY",
        "BACKUP_ALERT_EMAIL",
        "OWNER_ALERT_EMAIL",
        "ALERT_FROM_ADDRESS",
        "BACKUP_ALLOW_REMOTE_RESTORE",
    ]
    for name in names:
        monkeypatch.delenv(name, raising=False)
    values = {
        "BACKUP_DATABASE_URL": "postgresql://postgres:pw@127.0.0.1:5432/postgres",
        "BACKUP_S3_ENDPOINT_URL": "https://example.r2.cloudflarestorage.com",
        "BACKUP_S3_BUCKET": "agentnexlify-backups",
        "BACKUP_S3_ACCESS_KEY_ID": "test-access",
        "BACKUP_S3_SECRET_ACCESS_KEY": "test-secret",
        "RESEND_API_KEY": "test-resend-key",
        "BACKUP_ALERT_EMAIL": "ops@example.com",
    }
    values.update(overrides)
    for name, value in values.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


def stamp(moment: datetime) -> str:
    return moment.strftime("%Y%m%dT%H%M%SZ")


def test_retention_bounds():
    assert backup_common.parse_retention_days(None) == 21
    assert backup_common.parse_retention_days(" 14 ") == 14
    assert backup_common.parse_retention_days("30") == 30
    with pytest.raises(ConfigError, match="14 to 30"):
        backup_common.parse_retention_days("13")
    with pytest.raises(ConfigError, match="14 to 30"):
        backup_common.parse_retention_days("31")
    with pytest.raises(ConfigError, match="14 to 30"):
        backup_common.parse_retention_days("nope")


def test_keys_to_delete_only_expired_backup_objects():
    exactly_21 = PREFIX + f"agentnexlify-{stamp(NOW - timedelta(days=21))}.dump"
    inside_21 = PREFIX + f"agentnexlify-{stamp(NOW - timedelta(days=20, seconds=1))}.dump.enc"
    exactly_14 = PREFIX + f"agentnexlify-{stamp(NOW - timedelta(days=14))}.dump.age"
    inside_14 = PREFIX + f"agentnexlify-{stamp(NOW - timedelta(days=13) + timedelta(seconds=1))}.dump"
    keys = [
        exactly_21,
        inside_21,
        exactly_14,
        inside_14,
        PREFIX + "readme.txt",
        PREFIX + "nested/agentnexlify-20200101T000000Z.dump",
        "other/agentnexlify-20200101T000000Z.dump",
    ]
    doomed = backup_common.keys_to_delete(keys, prefix=PREFIX, now=NOW, retention_days=21)
    assert doomed == [exactly_21]
    doomed_14 = backup_common.keys_to_delete(keys, prefix=PREFIX, now=NOW, retention_days=14)
    assert exactly_14 in doomed_14
    assert exactly_21 in doomed_14
    assert inside_21 in doomed_14
    assert inside_14 not in doomed_14


def test_prefix_and_object_name():
    assert backup_common.normalize_prefix(None) == "supabase/"
    assert backup_common.normalize_prefix("nightly") == "nightly/"
    with pytest.raises(ConfigError):
        backup_common.normalize_prefix("../secrets/")
    assert backup_common.backup_object_name(NOW, "none").endswith(".dump")
    assert backup_common.backup_object_name(NOW, "aes-gcm").endswith(".dump.enc")
    assert backup_common.backup_object_name(NOW, "age").endswith(".dump.age")


def test_parse_url_rejects_transaction_pooler_and_prefers_session_fields():
    with pytest.raises(ConfigError, match="6543"):
        backup_common.parse_database_url(
            "postgresql://postgres.ref:pw@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
        )
    with pytest.raises(ConfigError, match="pgbouncer=true"):
        backup_common.parse_database_url(
            "postgresql://postgres:pw@db.example.supabase.co:5432/postgres?pgbouncer=true"
        )
    target = backup_common.parse_database_url(
        "postgresql://postgres.ref:p%40ss@[::1]:5432/app?sslmode=verify-full"
    )
    assert target.password == "p@ss"
    assert target.host == "::1"
    assert target.dbname == "app"
    assert target.sslmode == "verify-full"
    env = backup_common.libpq_env(target, app_name="agentnexlify-backup")
    assert env["PGSSLMODE"] == "verify-full"
    assert env["PGPASSWORD"] == "p@ss"
    remote = backup_common.parse_database_url(
        "postgresql://postgres:pw@db.example.supabase.co:5432/postgres"
    )
    assert backup_common.libpq_env(remote, app_name="agentnexlify-backup")["PGSSLMODE"] == "require"


def test_pg_dump_keeps_password_out_of_argv(monkeypatch, tmp_path):
    seen = {}

    def fake_run(cmd, env, **kwargs):
        seen["cmd"] = cmd
        seen["env"] = env
        file_flag = cmd.index("--file")
        Path(cmd[file_flag + 1]).write_bytes(b"PGDMPxxxx")

        class Completed:
            returncode = 0
            stderr = ""
            stdout = ""

        return Completed()

    monkeypatch.setattr(backup_common.subprocess, "run", fake_run)
    target = backup_common.parse_database_url(
        "postgresql://postgres:supersecret@127.0.0.1:5432/postgres"
    )
    output = tmp_path / "backup.dump"
    backup_common.run_pg_dump(target, output, pg_dump_bin="pg_dump")
    assert "supersecret" not in " ".join(seen["cmd"])
    assert seen["env"]["PGPASSWORD"] == "supersecret"
    assert "--format=custom" in seen["cmd"]
    assert "-Z" in seen["cmd"] and seen["cmd"][seen["cmd"].index("-Z") + 1] == "6"


def test_redact_strips_url_and_env_secrets(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "supersecret")
    text = backup_common.redact(
        "failed at postgresql://postgres:supersecret@db.example.co:5432/postgres supersecret"
    )
    assert "supersecret" not in text
    assert "postgresql://REDACTED" in text


def test_aes_roundtrip_and_wrong_key(tmp_path):
    src = tmp_path / "plain.dump"
    src.write_bytes(b"PGDMP" + b"x" * (1024 * 1024 + 100))
    enc = tmp_path / "agentnexlify-20261104T073000Z.dump.enc"
    backup_common.encrypt_aes_file(src, enc, "test-passphrase")
    assert backup_common.encryption_kind(enc) == "aes-gcm"
    out = tmp_path / "out.dump"
    backup_common.decrypt_aes_file(enc, out, "test-passphrase")
    assert out.read_bytes() == src.read_bytes()
    with pytest.raises(ConfigError, match="does not match"):
        backup_common.decrypt_aes_file(enc, tmp_path / "bad.dump", "other-passphrase")
    enc.write_bytes(b"nope")
    with pytest.raises(ConfigError, match="ANX1"):
        backup_common.decrypt_aes_file(enc, tmp_path / "bad2.dump", "test-passphrase")


def test_load_config_rules(monkeypatch):
    apply_env(monkeypatch, BACKUP_DATABASE_URL=None, DATABASE_URL=None, RESEND_API_KEY=None)
    with pytest.raises(ConfigError, match="BACKUP_DATABASE_URL"):
        backup.load_config()

    apply_env(
        monkeypatch,
        BACKUP_DATABASE_URL=None,
        DATABASE_URL="postgresql://postgres:pw@db.internal:5432/postgres",
    )
    cfg = backup.load_config()
    assert cfg.database_url_var == "DATABASE_URL"
    assert cfg.target.host == "db.internal"
    assert cfg.retention_days == 21
    assert cfg.prefix == "supabase/"

    apply_env(
        monkeypatch,
        BACKUP_DATABASE_URL="postgresql://postgres:pw@direct.internal:5432/postgres",
        DATABASE_URL="postgresql://postgres:pw@pooled.internal:6543/postgres",
    )
    assert backup.load_config().target.host == "direct.internal"

    apply_env(
        monkeypatch,
        BACKUP_DATABASE_URL="postgresql://postgres:pw@aws.pooler.supabase.com:6543/postgres",
    )
    with pytest.raises(ConfigError, match="6543"):
        backup.load_config()

    apply_env(monkeypatch, BACKUP_S3_ENDPOINT_URL="http://example.r2.cloudflarestorage.com")
    with pytest.raises(ConfigError, match="https"):
        backup.load_config()

    apply_env(monkeypatch, BACKUP_RETENTION_DAYS="31")
    with pytest.raises(ConfigError, match="14 to 30"):
        backup.load_config()

    apply_env(monkeypatch, BACKUP_AGE_RECIPIENT="not-a-key")
    with pytest.raises(ConfigError, match="age1"):
        backup.load_config()

    apply_env(monkeypatch, BACKUP_AGE_RECIPIENT="age1qqqqqqqqqqqqqqqqqqqq")
    monkeypatch.setattr(backup.shutil, "which", lambda _name: None)
    with pytest.raises(ConfigError, match="age binary"):
        backup.load_config()


def test_restore_guards_do_not_connect(monkeypatch):
    monkeypatch.delenv("BACKUP_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("BACKUP_ALLOW_REMOTE_RESTORE", raising=False)
    production = backup_common.parse_database_url(
        "postgresql://postgres.pxserpybmajixqrmzaly:pw@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
    )
    monkeypatch.setenv("BACKUP_ALLOW_REMOTE_RESTORE", "yes")
    with pytest.raises(ConfigError, match="pxserpybmajixqrmzaly"):
        backup_common.assert_restore_target_allowed(production)

    scratch = backup_common.parse_database_url(
        "postgresql://postgres.scratchproject:pw@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
    )
    monkeypatch.delenv("BACKUP_ALLOW_REMOTE_RESTORE", raising=False)
    with pytest.raises(ConfigError, match="Supabase host"):
        backup_common.assert_restore_target_allowed(scratch)
    monkeypatch.setenv("BACKUP_ALLOW_REMOTE_RESTORE", "yes")
    backup_common.assert_restore_target_allowed(scratch)

    local = backup_common.parse_database_url("postgresql://postgres@127.0.0.1:5432/restore_drill")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres@127.0.0.1:5432/restore_drill")
    with pytest.raises(ConfigError, match="source database"):
        backup_common.assert_restore_target_allowed(local)


class MemoryStore:
    def __init__(self):
        self.objects = {}
        self.deleted = []

    def upload(self, key, path):
        self.objects[key] = Path(path).read_bytes()

    def list_keys(self, prefix):
        return [key for key in self.objects if key.startswith(prefix)]

    def delete(self, keys):
        self.deleted.extend(keys)
        for key in keys:
            self.objects.pop(key, None)


def _cfg(monkeypatch, **overrides):
    apply_env(monkeypatch, **overrides)
    return backup.load_config()


def test_run_backup_uploads_then_prunes(monkeypatch, tmp_path):
    cfg = _cfg(monkeypatch)
    store = MemoryStore()
    old = PREFIX + f"agentnexlify-{stamp(NOW - timedelta(days=30))}.dump"
    kept = PREFIX + "readme.txt"
    store.objects[old] = b"old"
    store.objects[kept] = b"notes"

    def fake_dump(target, output, pg_dump_bin="pg_dump"):
        output.write_bytes(b"PGDMP-unit")
        output.chmod(0o600)

    monkeypatch.setattr(backup, "run_pg_dump", fake_dump)
    result = backup.run_backup(cfg, store=store, now=NOW, pg_dump_bin="pg_dump")
    assert result.key == PREFIX + f"agentnexlify-{stamp(NOW)}.dump"
    assert store.objects[result.key].startswith(b"PGDMP")
    assert old in store.deleted
    assert kept in store.objects
    assert result.encryption == "none"
    assert result.deleted == 1


def test_upload_failure_does_not_delete(monkeypatch):
    cfg = _cfg(monkeypatch)
    store = MemoryStore()
    old = PREFIX + "agentnexlify-20200101T000000Z.dump"
    store.objects[old] = b"old"

    def fake_dump(target, output, pg_dump_bin="pg_dump"):
        output.write_bytes(b"PGDMP-unit")

    def boom(key, path):
        raise RuntimeError("s3 down")

    monkeypatch.setattr(backup, "run_pg_dump", fake_dump)
    store.upload = boom
    with pytest.raises(RuntimeError, match="s3 down"):
        backup.run_backup(cfg, store=store, now=NOW, pg_dump_bin="pg_dump")
    assert old in store.objects
    assert store.deleted == []


def test_encrypted_backup_roundtrip_in_memory(monkeypatch):
    cfg = _cfg(monkeypatch, BACKUP_ENCRYPTION_KEY="test-passphrase")

    def fake_dump(target, output, pg_dump_bin="pg_dump"):
        output.write_bytes(b"PGDMP-secret")

    monkeypatch.setattr(backup, "run_pg_dump", fake_dump)
    store = MemoryStore()
    result = backup.run_backup(cfg, store=store, now=NOW, pg_dump_bin="pg_dump")
    assert result.key.endswith(".dump.enc")
    blob = next(iter(store.objects.values()))
    with TemporaryDirectory() as directory:
        path = Path(directory) / "blob.dump.enc"
        path.write_bytes(blob)
        plain = Path(directory) / "plain.dump"
        backup_common.decrypt_aes_file(path, plain, "test-passphrase")
        assert plain.read_bytes() == b"PGDMP-secret"


def test_age_recipient_wins_over_passphrase(monkeypatch, capsys):
    cfg = _cfg(
        monkeypatch,
        BACKUP_AGE_RECIPIENT="age1qqqqqqqqqqqqqqqqqqqq",
        BACKUP_ENCRYPTION_KEY="test-passphrase",
    )

    def fake_dump(target, output, pg_dump_bin="pg_dump"):
        output.write_bytes(b"PGDMP-age")

    def fake_age(src, dst, recipient):
        dst.write_bytes(b"AGE" + src.read_bytes())

    monkeypatch.setattr(backup, "run_pg_dump", fake_dump)
    monkeypatch.setattr(backup_common, "run_age_encrypt", fake_age)
    store = MemoryStore()
    result = backup.run_backup(cfg, store=store, now=NOW, pg_dump_bin="pg_dump")
    assert result.encryption == "age"
    assert result.key.endswith(".dump.age")
    assert b"test-passphrase" not in next(iter(store.objects.values()))
    assert "BACKUP_ENCRYPTION_KEY is not used" in capsys.readouterr().out


def test_failure_emails_resend_without_secrets(monkeypatch):
    apply_env(
        monkeypatch,
        BACKUP_DATABASE_URL="postgresql://postgres:supersecret@127.0.0.1:5432/postgres",
        BACKUP_ENCRYPTION_KEY="supersecret",
    )
    sent = {}

    def boom(cfg, **kwargs):
        raise RuntimeError(
            "could not connect to postgresql://postgres:supersecret@127.0.0.1:5432/postgres"
        )

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"{}"

    def fake_urlopen(request, timeout=0):
        sent["url"] = request.full_url
        sent["body"] = request.data.decode()
        sent["auth"] = request.get_header("Authorization")
        return Response()

    monkeypatch.setattr(backup, "run_backup", boom)
    monkeypatch.setattr(backup.urllib.request, "urlopen", fake_urlopen)
    assert backup.main() == 1
    assert sent["url"] == backup.RESEND_URL
    assert sent["auth"] == "Bearer test-resend-key"
    assert "supersecret" not in sent["body"]
    assert "test-resend-key" not in sent["body"]
    assert "ops@example.com" in sent["body"]
    assert "Postgres backup failed" in sent["body"]


def test_alert_failure_still_exits_nonzero(monkeypatch):
    apply_env(monkeypatch)

    def boom(cfg, **kwargs):
        raise RuntimeError("disk full")

    def fake_urlopen(request, timeout=0):
        raise backup.urllib.error.HTTPError(backup.RESEND_URL, 403, "no", hdrs=None, fp=None)

    monkeypatch.setattr(backup, "run_backup", boom)
    monkeypatch.setattr(backup.urllib.request, "urlopen", fake_urlopen)
    assert backup.main() == 1


def test_missing_alert_config_exits_nonzero_without_email(monkeypatch, capsys):
    apply_env(monkeypatch, RESEND_API_KEY=None, BACKUP_ALERT_EMAIL=None)
    assert backup.main() == 1
    captured = capsys.readouterr()
    assert "failure alert not sent" in captured.err
