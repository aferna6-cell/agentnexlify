"""Tests for OAuth-token at-rest encryption helpers (GH #266 step 2).

Contracts:
  - encrypt_oauth_tokens dual-writes ciphertext columns when a key is
    configured, and is a strict no-op when no key is set (prod today).
  - decrypt_integration_row prefers ciphertext, falls back to plaintext on
    missing ciphertext or decrypt failure, and no-ops without a key.
  - round-trip through both helpers restores the original token values.
"""

from unittest.mock import patch

from cryptography.fernet import Fernet

from backend.services import integration_key_vault as vault

KEY_A = Fernet.generate_key().decode()
KEY_B = Fernet.generate_key().decode()


def _with_key(key):
    return patch.object(vault.settings, "integrations_enc_key", key)


def _without_keys():
    from contextlib import ExitStack

    stack = ExitStack()
    stack.enter_context(patch.object(vault.settings, "integrations_enc_key", ""))
    stack.enter_context(patch.object(vault.settings, "integrations_enc_keys", ""))
    return stack


class TestEncryptOauthTokens:
    def test_no_key_is_noop(self):
        payload = {"access_token": "at-secret", "refresh_token": "rt-secret"}
        with _without_keys():
            out = vault.encrypt_oauth_tokens(payload)
        assert out == payload
        assert "access_token_enc" not in out

    def test_dual_writes_both_tokens(self):
        payload = {"access_token": "at-secret", "refresh_token": "rt-secret"}
        with _with_key(KEY_A):
            out = vault.encrypt_oauth_tokens(payload)
            # Ciphertext decrypts back to the original
            decrypted = vault.decrypt_key(vault._from_bytea(out["access_token_enc"]))
        assert out["access_token"] == "at-secret"  # plaintext retained pre-sunset
        assert out["access_token_enc"].startswith("\\x")
        assert out["refresh_token_enc"].startswith("\\x")
        assert decrypted == "at-secret"

    def test_missing_refresh_token_skipped(self):
        with _with_key(KEY_A):
            out = vault.encrypt_oauth_tokens({"access_token": "at-only"})
        assert "access_token_enc" in out
        assert "refresh_token_enc" not in out


class TestDecryptIntegrationRow:
    def test_none_row_passthrough(self):
        with _with_key(KEY_A):
            assert vault.decrypt_integration_row(None) is None

    def test_no_key_passthrough(self):
        row = {"access_token": "plain", "access_token_enc": "\\xdeadbeef"}
        with _without_keys():
            assert vault.decrypt_integration_row(row) == row

    def test_prefers_ciphertext_over_plaintext(self):
        with _with_key(KEY_A):
            enc = vault._to_bytea(vault.encrypt_key("fresh-token"))
            row = {
                "access_token": "stale-plaintext",
                "access_token_enc": enc,
                "metadata": {},
            }
            out = vault.decrypt_integration_row(row)
        assert out["access_token"] == "fresh-token"

    def test_falls_back_to_plaintext_when_no_ciphertext(self):
        with _with_key(KEY_A):
            row = {"access_token": "plain-only", "access_token_enc": None}
            out = vault.decrypt_integration_row(row)
        assert out["access_token"] == "plain-only"

    def test_wrong_key_falls_back_to_plaintext(self):
        with _with_key(KEY_A):
            enc = vault._to_bytea(vault.encrypt_key("secret"))
        row = {"access_token": "plaintext-fallback", "access_token_enc": enc}
        with _with_key(KEY_B):  # different key — decrypt raises internally
            out = vault.decrypt_integration_row(row)
        assert out["access_token"] == "plaintext-fallback"

    def test_round_trip_via_write_helper(self):
        with _with_key(KEY_A):
            written = vault.encrypt_oauth_tokens(
                {"access_token": "at-rt", "refresh_token": "rt-rt"}
            )
            # Simulate the post-sunset world: plaintext columns gone
            stored = {
                "access_token_enc": written["access_token_enc"],
                "refresh_token_enc": written["refresh_token_enc"],
                "metadata": {},
            }
            out = vault.decrypt_integration_row(stored)
        assert out["access_token"] == "at-rt"
        assert out["refresh_token"] == "rt-rt"
