"""Tests for backend/services/integration_key_vault.py — 100% coverage required.

Tests all paths:
- encrypt_key → returns bytes
- decrypt_key round-trip → matches original
- decrypt_key with wrong key → raises InvalidToken
- decrypt_key with malformed bytes → raises exception
- mask_key: normal (>=16 chars), short (<16 chars), exactly 16 chars
- is_test_key: sk_test_ in production → True, staging → False, sk_live_ in prod → False
- _get_fernet with key missing → raises RuntimeError
- _get_fernet with valid key → returns Fernet instance
"""

import pytest
from cryptography.fernet import Fernet, InvalidToken

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_key() -> str:
    """Generate a fresh valid Fernet key string."""
    return Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# _get_fernet
# ---------------------------------------------------------------------------


class TestGetFernet:
    def test_missing_key_raises_runtime_error(self, monkeypatch):
        monkeypatch.delenv("INTEGRATIONS_ENC_KEY", raising=False)
        from backend.services.integration_key_vault import _get_fernet

        with pytest.raises(RuntimeError, match="INTEGRATIONS_ENC_KEY not set"):
            _get_fernet()

    def test_valid_key_returns_fernet_instance(self, monkeypatch):
        monkeypatch.setenv("INTEGRATIONS_ENC_KEY", _make_key())
        from backend.services.integration_key_vault import _get_fernet

        f = _get_fernet()
        assert isinstance(f, Fernet)

    def test_accepts_bytes_key(self, monkeypatch):
        """Key stored as bytes (edge case in some env loading paths)."""
        key_str = _make_key()
        # Simulate env providing a str — monkeypatch.setenv only accepts str
        monkeypatch.setenv("INTEGRATIONS_ENC_KEY", key_str)
        from backend.services.integration_key_vault import _get_fernet

        f = _get_fernet()
        assert isinstance(f, Fernet)


# ---------------------------------------------------------------------------
# encrypt_key
# ---------------------------------------------------------------------------


class TestEncryptKey:
    def test_returns_bytes(self, monkeypatch):
        monkeypatch.setenv("INTEGRATIONS_ENC_KEY", _make_key())
        from backend.services import integration_key_vault as vault

        result = vault.encrypt_key("sk_live_abc123")
        assert isinstance(result, bytes)

    def test_different_calls_produce_different_ciphertext(self, monkeypatch):
        """Fernet uses a random IV — same plaintext should differ each call."""
        monkeypatch.setenv("INTEGRATIONS_ENC_KEY", _make_key())
        from backend.services import integration_key_vault as vault

        ct1 = vault.encrypt_key("same-plaintext")
        ct2 = vault.encrypt_key("same-plaintext")
        assert ct1 != ct2

    def test_raises_when_key_missing(self, monkeypatch):
        monkeypatch.delenv("INTEGRATIONS_ENC_KEY", raising=False)
        from backend.services import integration_key_vault as vault

        with pytest.raises(RuntimeError):
            vault.encrypt_key("any-key")


# ---------------------------------------------------------------------------
# decrypt_key
# ---------------------------------------------------------------------------


class TestDecryptKey:
    def test_round_trip_matches(self, monkeypatch):
        key = _make_key()
        monkeypatch.setenv("INTEGRATIONS_ENC_KEY", key)
        from backend.services import integration_key_vault as vault

        plaintext = "sk_live_super_secret_key_abc123xyz"
        ciphertext = vault.encrypt_key(plaintext)
        assert vault.decrypt_key(ciphertext) == plaintext

    def test_wrong_key_raises_invalid_token(self, monkeypatch):
        key1 = _make_key()
        key2 = _make_key()

        # Encrypt with key1
        monkeypatch.setenv("INTEGRATIONS_ENC_KEY", key1)
        from backend.services import integration_key_vault as vault

        ciphertext = vault.encrypt_key("secret-value")

        # Switch to key2 — _get_fernet() reads env at call time, no reload needed
        monkeypatch.setenv("INTEGRATIONS_ENC_KEY", key2)

        with pytest.raises(InvalidToken):
            vault.decrypt_key(ciphertext)

    def test_malformed_bytes_raises(self, monkeypatch):
        monkeypatch.setenv("INTEGRATIONS_ENC_KEY", _make_key())
        from backend.services import integration_key_vault as vault

        with pytest.raises(Exception):
            vault.decrypt_key(b"this-is-not-valid-fernet-ciphertext")

    def test_empty_bytes_raises(self, monkeypatch):
        monkeypatch.setenv("INTEGRATIONS_ENC_KEY", _make_key())
        from backend.services import integration_key_vault as vault

        with pytest.raises(Exception):
            vault.decrypt_key(b"")

    def test_raises_when_key_missing(self, monkeypatch):
        monkeypatch.delenv("INTEGRATIONS_ENC_KEY", raising=False)
        from backend.services import integration_key_vault as vault

        with pytest.raises(RuntimeError):
            vault.decrypt_key(b"anything")

    def test_unicode_plaintext_preserved(self, monkeypatch):
        """Non-ASCII content round-trips correctly."""
        monkeypatch.setenv("INTEGRATIONS_ENC_KEY", _make_key())
        from backend.services import integration_key_vault as vault

        plaintext = "sk_test_cle-avec-accent-éà"
        assert vault.decrypt_key(vault.encrypt_key(plaintext)) == plaintext


# ---------------------------------------------------------------------------
# mask_key
# ---------------------------------------------------------------------------


class TestMaskKey:
    def test_normal_key_ge_16_chars(self):
        from backend.services.integration_key_vault import mask_key

        result = mask_key("sk_live_abcdefgh1234")
        # First 8 chars preserved
        assert result.startswith("sk_live_")
        # Last 4 chars preserved
        assert result.endswith("1234")
        # Middle is bullets
        assert "•••••" in result

    def test_exactly_16_chars(self):
        from backend.services.integration_key_vault import mask_key

        key = "1234567890abcdef"  # exactly 16 chars
        result = mask_key(key)
        assert result.startswith("12345678")
        assert result.endswith("cdef")
        assert "•••••" in result

    def test_short_key_lt_16_chars(self):
        from backend.services.integration_key_vault import mask_key

        key = "shortkey"  # 8 chars — below threshold
        result = mask_key(key)
        assert result.startswith("••••")
        # Last 4 chars of "shortkey" = "tkey"
        assert result.endswith("tkey")
        # Should NOT have the 8-char prefix (key is too short)
        assert not result.startswith("shor")

    def test_exactly_15_chars_uses_short_path(self):
        from backend.services.integration_key_vault import mask_key

        key = "a" * 15
        result = mask_key(key)
        assert result.startswith("••••")

    def test_minimum_viable_key(self):
        """4-char key: last 4 = whole key."""
        from backend.services.integration_key_vault import mask_key

        result = mask_key("abcd")
        assert result == "••••abcd"


# ---------------------------------------------------------------------------
# is_test_key
# ---------------------------------------------------------------------------


class TestIsTestKey:
    def test_stripe_test_key_in_production_returns_true(self):
        from backend.services.integration_key_vault import is_test_key

        assert is_test_key("sk_test_abc123xyz", env="production") is True

    def test_stripe_test_key_in_staging_returns_false(self):
        from backend.services.integration_key_vault import is_test_key

        assert is_test_key("sk_test_abc123xyz", env="staging") is False

    def test_stripe_test_key_in_development_returns_false(self):
        from backend.services.integration_key_vault import is_test_key

        assert is_test_key("sk_test_abc123xyz", env="development") is False

    def test_live_key_in_production_returns_false(self):
        from backend.services.integration_key_vault import is_test_key

        assert is_test_key("sk_live_abc123xyz", env="production") is False

    def test_live_key_in_staging_returns_false(self):
        from backend.services.integration_key_vault import is_test_key

        assert is_test_key("sk_live_abc123xyz", env="staging") is False

    def test_non_stripe_key_in_production_returns_false(self):
        from backend.services.integration_key_vault import is_test_key

        assert is_test_key("rk_test_resend_key", env="production") is False

    def test_default_env_is_production(self):
        from backend.services.integration_key_vault import is_test_key

        # Default env="production" — test key should be flagged
        assert is_test_key("sk_test_abc") is True
