"""100% line+branch coverage for the integration key vault (GH #131).

Security-critical: the CI gate runs
``pytest --cov=backend.services.integration_key_vault --cov-fail-under=100``.

Real Fernet keys are generated per-test and injected via the settings singleton;
the DB is a fake that records writes, so every branch is exercised hermetically.
"""

import pytest
from cryptography.fernet import Fernet

from backend.services import integration_key_vault as iv


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, table):
        self._db = db
        self._table = table
        self._op = "select"
        self._payload = None

    def select(self, *a, **k):
        self._op = "select"
        return self

    def upsert(self, payload, **k):
        self._op = "upsert"
        self._payload = payload
        return self

    def update(self, payload, **k):
        self._op = "update"
        self._payload = payload
        return self

    def insert(self, payload, **k):
        self._op = "insert"
        self._payload = payload
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self._table == "audit_log" and self._db.audit_raises:
            raise RuntimeError("relation audit_log does not exist")
        if self._op == "select":
            return _Result(list(self._db.integration_rows))
        self._db.writes.append((self._table, self._op, self._payload))
        return _Result([])


class _FakeDB:
    def __init__(self, integration_rows=None, audit_raises=False):
        self.integration_rows = integration_rows or []
        self.audit_raises = audit_raises
        self.writes = []

    def table(self, name):
        return _Query(self, name)


@pytest.fixture
def key1():
    return Fernet.generate_key().decode()


@pytest.fixture
def key2():
    return Fernet.generate_key().decode()


def _set_keys(monkeypatch, primary="", extra=""):
    monkeypatch.setattr(iv.settings, "integrations_enc_key", primary)
    monkeypatch.setattr(iv.settings, "integrations_enc_keys", extra)


# --------------------------------------------------------------------------- #
# _key_map
# --------------------------------------------------------------------------- #


def test_key_map_primary_and_extra(monkeypatch, key1, key2):
    _set_keys(monkeypatch, primary=key1, extra=f"  , x:nope , 3: , 5:{key2}")
    m = iv._key_map()
    assert m[1] == key1
    assert m[5] == key2
    assert 3 not in m  # empty key skipped
    assert "x" not in m  # non-digit version skipped


def test_key_map_empty(monkeypatch):
    _set_keys(monkeypatch)
    assert iv._key_map() == {}


# --------------------------------------------------------------------------- #
# _fernet
# --------------------------------------------------------------------------- #


def test_fernet_missing_version_raises(monkeypatch):
    _set_keys(monkeypatch)
    with pytest.raises(iv.IntegrationKeyVaultError):
        iv._fernet(1)


def test_fernet_malformed_key_raises(monkeypatch):
    _set_keys(monkeypatch, primary="not-a-valid-fernet-key")
    with pytest.raises(iv.IntegrationKeyVaultError):
        iv._fernet(1)


# --------------------------------------------------------------------------- #
# encrypt / decrypt round-trip + failure modes
# --------------------------------------------------------------------------- #


def test_encrypt_decrypt_roundtrip(monkeypatch, key1):
    _set_keys(monkeypatch, primary=key1)
    token = iv.encrypt_key("sk_live_secret_value")
    assert isinstance(token, bytes)
    assert iv.decrypt_key(token) == "sk_live_secret_value"


def test_encrypt_empty_raises(monkeypatch, key1):
    _set_keys(monkeypatch, primary=key1)
    with pytest.raises(iv.IntegrationKeyVaultError):
        iv.encrypt_key("")


def test_decrypt_none_returns_none(monkeypatch, key1):
    _set_keys(monkeypatch, primary=key1)
    assert iv.decrypt_key(None) is None


def test_decrypt_wrong_key_raises(monkeypatch, key1, key2):
    _set_keys(monkeypatch, primary=key1, extra=f"2:{key2}")
    token = iv.encrypt_key("secret", version=1)
    with pytest.raises(iv.IntegrationKeyVaultError):
        iv.decrypt_key(token, version=2)  # wrong key version


def test_decrypt_malformed_raises(monkeypatch, key1):
    _set_keys(monkeypatch, primary=key1)
    with pytest.raises(iv.IntegrationKeyVaultError):
        iv.decrypt_key(b"not-a-valid-token")


# --------------------------------------------------------------------------- #
# mask_key
# --------------------------------------------------------------------------- #


def test_mask_empty():
    assert iv.mask_key("") == ""


def test_mask_short():
    assert iv.mask_key("short") == "s••••"
    assert iv.mask_key("abcdefghijkl") == "a••••"  # exactly 12 -> short branch


def test_mask_normal():
    assert iv.mask_key("sk_live_0000000000001234") == "sk_live_••••1234"


# --------------------------------------------------------------------------- #
# _from_bytea
# --------------------------------------------------------------------------- #


def test_from_bytea_variants():
    assert iv._from_bytea(None) is None
    assert iv._from_bytea(b"\x01\x02") == b"\x01\x02"
    assert iv._from_bytea(bytearray(b"\x03")) == b"\x03"
    assert iv._from_bytea("\\x0102") == b"\x01\x02"
    assert iv._from_bytea("0102") == b"\x01\x02"
    with pytest.raises(iv.IntegrationKeyVaultError):
        iv._from_bytea(12345)


# --------------------------------------------------------------------------- #
# _write_audit
# --------------------------------------------------------------------------- #


def test_write_audit_success():
    db = _FakeDB()
    iv._write_audit(db, "ten1", "stripe")
    assert any(t == "audit_log" and op == "insert" for (t, op, _p) in db.writes)


def test_write_audit_failure_swallowed():
    db = _FakeDB(audit_raises=True)
    iv._write_audit(db, "ten1", "stripe")  # must not raise
    assert db.writes == []


# --------------------------------------------------------------------------- #
# save_integration_key
# --------------------------------------------------------------------------- #


def test_save_writes_encrypted_only(monkeypatch, key1):
    _set_keys(monkeypatch, primary=key1)
    db = _FakeDB()
    monkeypatch.setattr(iv, "get_service_supabase", lambda: db)

    out = iv.save_integration_key("ten1", "stripe", "sk_live_0000000000001234", {"x": 1})
    assert out["masked"] == "sk_live_••••1234"
    assert out["enc_key_version"] == 1

    upserts = [p for (t, op, p) in db.writes if t == "integrations" and op == "upsert"]
    assert len(upserts) == 1
    payload = upserts[0]
    assert payload["access_token_enc"].startswith("\\x")
    assert "access_token" not in payload  # plaintext never written
    assert payload["metadata"]["enc_key_version"] == 1
    assert payload["metadata"]["x"] == 1


def test_save_with_audit_failure_still_succeeds(monkeypatch, key1):
    _set_keys(monkeypatch, primary=key1)
    db = _FakeDB(audit_raises=True)
    monkeypatch.setattr(iv, "get_service_supabase", lambda: db)
    out = iv.save_integration_key("ten1", "twilio", "secretvalue123456")
    assert out["provider"] == "twilio"


# --------------------------------------------------------------------------- #
# load_integration_key
# --------------------------------------------------------------------------- #


def test_load_no_row_returns_none(monkeypatch, key1):
    _set_keys(monkeypatch, primary=key1)
    monkeypatch.setattr(iv, "get_service_supabase", lambda: _FakeDB(integration_rows=[]))
    assert iv.load_integration_key("ten1", "stripe") is None


def test_load_null_ciphertext_returns_none(monkeypatch, key1):
    _set_keys(monkeypatch, primary=key1)
    rows = [{"access_token_enc": None, "metadata": {}}]
    monkeypatch.setattr(iv, "get_service_supabase", lambda: _FakeDB(integration_rows=rows))
    assert iv.load_integration_key("ten1", "stripe") is None


def test_load_roundtrip(monkeypatch, key1):
    _set_keys(monkeypatch, primary=key1)
    token = iv.encrypt_key("sk_live_roundtrip", 1)
    rows = [{"access_token_enc": iv._to_bytea(token), "metadata": {"enc_key_version": 1}}]
    monkeypatch.setattr(iv, "get_service_supabase", lambda: _FakeDB(integration_rows=rows))
    assert iv.load_integration_key("ten1", "stripe") == "sk_live_roundtrip"


# --------------------------------------------------------------------------- #
# rotate_key
# --------------------------------------------------------------------------- #


def test_rotate_no_row_raises(monkeypatch, key1):
    _set_keys(monkeypatch, primary=key1)
    monkeypatch.setattr(iv, "get_service_supabase", lambda: _FakeDB(integration_rows=[]))
    with pytest.raises(iv.IntegrationKeyVaultError):
        iv.rotate_key("ten1", "stripe", 1, 2)


def test_rotate_null_ciphertext_raises(monkeypatch, key1):
    _set_keys(monkeypatch, primary=key1)
    rows = [{"access_token_enc": None, "metadata": {}}]
    monkeypatch.setattr(iv, "get_service_supabase", lambda: _FakeDB(integration_rows=rows))
    with pytest.raises(iv.IntegrationKeyVaultError):
        iv.rotate_key("ten1", "stripe", 1, 2)


def test_rotate_happy_path(monkeypatch, key1, key2):
    _set_keys(monkeypatch, primary=key1, extra=f"2:{key2}")
    token_v1 = iv.encrypt_key("sk_live_rotate_me", 1)
    rows = [{"access_token_enc": iv._to_bytea(token_v1), "metadata": {"enc_key_version": 1}}]
    db = _FakeDB(integration_rows=rows)
    monkeypatch.setattr(iv, "get_service_supabase", lambda: db)

    out = iv.rotate_key("ten1", "stripe", 1, 2)
    assert out["enc_key_version"] == 2

    updates = [p for (t, op, p) in db.writes if t == "integrations" and op == "update"]
    assert len(updates) == 1
    new_enc = iv._from_bytea(updates[0]["access_token_enc"])
    assert iv.decrypt_key(new_enc, 2) == "sk_live_rotate_me"
    assert updates[0]["metadata"]["enc_key_version"] == 2


def test_rotate_wrong_old_version_raises(monkeypatch, key1, key2):
    _set_keys(monkeypatch, primary=key1, extra=f"2:{key2}")
    token_v1 = iv.encrypt_key("secret", 1)
    rows = [{"access_token_enc": iv._to_bytea(token_v1), "metadata": {"enc_key_version": 1}}]
    monkeypatch.setattr(iv, "get_service_supabase", lambda: _FakeDB(integration_rows=rows))
    with pytest.raises(iv.IntegrationKeyVaultError):
        iv.rotate_key("ten1", "stripe", 2, 1)  # decrypt with wrong (v2) key fails


def test_load_metadata_none_uses_default_version(monkeypatch, key1):
    # Covers the `metadata or {}` falsy branch in load_integration_key.
    _set_keys(monkeypatch, primary=key1)
    token = iv.encrypt_key("sk_live_defaultver", 1)
    rows = [{"access_token_enc": iv._to_bytea(token), "metadata": None}]
    monkeypatch.setattr(iv, "get_service_supabase", lambda: _FakeDB(integration_rows=rows))
    assert iv.load_integration_key("ten1", "stripe") == "sk_live_defaultver"


def test_rotate_metadata_none(monkeypatch, key1, key2):
    # Covers the `metadata or {}` falsy branch in rotate_key.
    _set_keys(monkeypatch, primary=key1, extra=f"2:{key2}")
    token_v1 = iv.encrypt_key("sk_live_nometa", 1)
    rows = [{"access_token_enc": iv._to_bytea(token_v1), "metadata": None}]
    db = _FakeDB(integration_rows=rows)
    monkeypatch.setattr(iv, "get_service_supabase", lambda: db)
    out = iv.rotate_key("ten1", "stripe", 1, 2)
    assert out["enc_key_version"] == 2
    updates = [p for (t, op, p) in db.writes if t == "integrations" and op == "update"]
    assert updates[0]["metadata"]["enc_key_version"] == 2
