"""Dump and restore against a Postgres that this file starts on 127.0.0.1.

These tests are outside pytest's default testpaths (`tests/` and the CI
invocation of `backend/tests/`), so GitHub Actions does not collect them.
They never open a Supabase host.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import backup_common

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.timeout(180)


def postgres_bin_dir() -> Path | None:
    found = shutil.which("initdb")
    if found:
        return Path(found).resolve().parent
    candidates = sorted(Path("/usr/lib/postgresql").glob("*/bin/initdb"))
    if not candidates:
        return None
    return candidates[-1].parent


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def postgres_server():
    bin_dir = postgres_bin_dir()
    if bin_dir is None:
        pytest.skip("PostgreSQL server binaries are not installed")
    data = Path(tempfile.mkdtemp(prefix="anx-pgdata-"))
    sock_dir = Path(tempfile.mkdtemp(prefix="anx-pgsock-"))
    env = os.environ.copy()
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    env["LC_ALL"] = "C.UTF-8"
    env["LANG"] = "C.UTF-8"
    env["PGCLIENTENCODING"] = "UTF8"
    init = subprocess.run(
        [
            str(bin_dir / "initdb"),
            "-D",
            str(data),
            "-U",
            "postgres",
            "--auth-local=trust",
            "--auth-host=trust",
            "--encoding=UTF8",
            "--locale=C",
            "--no-instructions",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if init.returncode != 0:
        pytest.fail(f"initdb failed\n{init.stderr}\n{init.stdout}")
    port = free_port()
    log = data / "server.log"
    start = subprocess.run(
        [
            str(bin_dir / "pg_ctl"),
            "-D",
            str(data),
            "-l",
            str(log),
            "-w",
            "-t",
            "60",
            "start",
            "-o",
            (
                f"-h 127.0.0.1 -p {port} -k {sock_dir} "
                f"-c unix_socket_directories={sock_dir} "
                "-c listen_addresses=127.0.0.1 -c fsync=off"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if start.returncode != 0:
        logged = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        pytest.fail(f"pg_ctl start failed\n{start.stderr}\n{logged}")
    yield {"bin": bin_dir, "port": port, "env": env}
    subprocess.run(
        [str(bin_dir / "pg_ctl"), "-D", str(data), "-m", "fast", "-w", "stop"],
        check=False,
        env=env,
    )
    shutil.rmtree(data, ignore_errors=True)
    shutil.rmtree(sock_dir, ignore_errors=True)


def local_url(server, dbname: str) -> str:
    url = f"postgresql://postgres@127.0.0.1:{server['port']}/{dbname}?sslmode=disable"
    target = backup_common.parse_database_url(url)
    assert target.host == "127.0.0.1"
    assert "supabase" not in target.host
    return url


def psql(server, dbname: str, sql: str) -> str:
    completed = subprocess.run(
        [
            str(server["bin"] / "psql"),
            "-h",
            "127.0.0.1",
            "-p",
            str(server["port"]),
            "-U",
            "postgres",
            "-d",
            dbname,
            "-v",
            "ON_ERROR_STOP=1",
            "-tAc",
            sql,
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**server["env"], "PGSSLMODE": "disable"},
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def createdb(server, dbname: str) -> None:
    completed = subprocess.run(
        [
            str(server["bin"] / "createdb"),
            "-h",
            "127.0.0.1",
            "-p",
            str(server["port"]),
            "-U",
            "postgres",
            dbname,
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**server["env"], "PGSSLMODE": "disable"},
    )
    assert completed.returncode == 0, completed.stderr


def restore_env(server) -> dict[str, str]:
    env = server["env"].copy()
    for name in (
        "BACKUP_DATABASE_URL",
        "DATABASE_URL",
        "PGPASSWORD",
        "PGHOST",
        "PGPORT",
        "PGUSER",
        "PGDATABASE",
        "BACKUP_ALLOW_REMOTE_RESTORE",
        "BACKUP_ENCRYPTION_KEY",
    ):
        env.pop(name, None)
    env["PGSSLMODE"] = "disable"
    return env


def run_restore(server, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "restore.py"), *args],
        check=False,
        capture_output=True,
        text=True,
        env=restore_env(server),
    )


@pytest.fixture(scope="module")
def source_dump(postgres_server, tmp_path_factory):
    createdb(postgres_server, "backup_src")
    psql(
        postgres_server,
        "backup_src",
        "CREATE TABLE backup_sentinel (id integer PRIMARY KEY, note text NOT NULL); "
        "INSERT INTO backup_sentinel (id, note) VALUES "
        "(1, 'offsite-backup-ok-café'), (2, 'second-row');",
    )
    dump = tmp_path_factory.mktemp("dumps") / "source.dump"
    target = backup_common.parse_database_url(local_url(postgres_server, "backup_src"))
    backup_common.run_pg_dump(
        target,
        dump,
        pg_dump_bin=str(postgres_server["bin"] / "pg_dump"),
    )
    assert dump.read_bytes()[:5] == b"PGDMP"
    return dump


def assert_restored(server, dbname: str) -> None:
    assert psql(server, dbname, "SELECT note FROM backup_sentinel WHERE id = 1") == (
        "offsite-backup-ok-café"
    )
    assert psql(server, dbname, "SELECT count(*) FROM backup_sentinel") == "2"


def test_plain_dump_restores_into_local_postgres(postgres_server, source_dump, tmp_path):
    createdb(postgres_server, "backup_dst_plain")
    archive = tmp_path / "agentnexlify-20261104T073000Z.dump"
    shutil.copy(source_dump, archive)
    completed = run_restore(
        postgres_server,
        [
            "--input",
            str(archive),
            "--target-url",
            local_url(postgres_server, "backup_dst_plain"),
            "--schema",
            "public",
        ],
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert "restore complete" in completed.stdout
    assert_restored(postgres_server, "backup_dst_plain")


def test_encrypted_dump_restores_into_local_postgres(postgres_server, source_dump, tmp_path):
    createdb(postgres_server, "backup_dst_enc")
    src = tmp_path / "agentnexlify-20261104T073100Z.dump"
    shutil.copy(source_dump, src)
    enc, mode = backup_common.encrypt_backup_file(
        src,
        age_recipient="",
        encryption_key="test-passphrase",
    )
    assert mode == "aes-gcm"
    assert enc.name.endswith(".dump.enc")
    completed = run_restore(
        postgres_server,
        [
            "--input",
            str(enc),
            "--target-url",
            local_url(postgres_server, "backup_dst_enc"),
            "--encryption-key",
            "test-passphrase",
        ],
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert_restored(postgres_server, "backup_dst_enc")


def test_age_dump_restores_into_local_postgres(postgres_server, source_dump, tmp_path):
    if shutil.which("age-keygen") is None or shutil.which("age") is None:
        pytest.skip("age is not installed")
    createdb(postgres_server, "backup_dst_age")
    identity = tmp_path / "backup-age.key"
    keygen = subprocess.run(
        ["age-keygen", "-o", str(identity)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert keygen.returncode == 0, keygen.stderr
    os.chmod(identity, 0o600)
    recipient = ""
    for line in identity.read_text(encoding="utf-8").splitlines():
        if line.startswith("# public key:"):
            recipient = line.split(":", 1)[1].strip()
    assert recipient.startswith("age1")
    src = tmp_path / "agentnexlify-20261104T073200Z.dump"
    shutil.copy(source_dump, src)
    encrypted, mode = backup_common.encrypt_backup_file(
        src,
        age_recipient=recipient,
        encryption_key="",
    )
    assert mode == "age"
    completed = run_restore(
        postgres_server,
        [
            "--input",
            str(encrypted),
            "--target-url",
            local_url(postgres_server, "backup_dst_age"),
            "--age-identity",
            str(identity),
        ],
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert_restored(postgres_server, "backup_dst_age")
