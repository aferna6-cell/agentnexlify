"""Encrypt integration secrets (Stripe / Twilio / Resend API keys) at rest.

Tenants paste third-party API keys via Settings. Those keys are encrypted to a
Fernet token (AES-128-CBC + HMAC, authenticated) and stored in
``integrations.access_token_enc`` (BYTEA, migration 148). The plaintext
``access_token`` column is retained until a separate sunset migration after
backfill is verified (user-rules Rule 8).

Encryption is app-side via ``cryptography.fernet`` rather than in-DB pgcrypto.
The onboarding-v2 spec §9 sanctions this; it lets the vault be unit-tested to
100% line+branch coverage without a live database, and Fernet raises
``InvalidToken`` on wrong-key / tampered / malformed input — exactly the
fail-closed behavior the spec requires.

Security invariants:
- Plaintext keys are NEVER logged. save/load/rotate log only tenant_id + provider.
- Wrong key or corrupt ciphertext raises ``IntegrationKeyVaultError`` — it never
  silently returns an empty string.
- A missing encryption key raises (fail closed), it does not encrypt with a default.

GH #129 (migration) + #131 (this service).
"""

import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from backend.config import settings
from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

DEFAULT_KEY_VERSION = 1


class IntegrationKeyVaultError(Exception):
    """Raised when encryption/decryption fails or no key is configured."""


def _key_map() -> dict[int, str]:
    """Resolve {version: base64-key} from settings.

    Version 1 comes from ``integrations_enc_key``. Older versions for rotation
    come from ``integrations_enc_keys`` formatted as ``"2:keyB,3:keyC"``.
    """
    keys: dict[int, str] = {}
    if settings.integrations_enc_key:
        keys[DEFAULT_KEY_VERSION] = settings.integrations_enc_key
    for part in (settings.integrations_enc_keys or "").split(","):
        part = part.strip()
        if not part:
            continue
        version_str, _, key_str = part.partition(":")
        version_str = version_str.strip()
        key_str = key_str.strip()
        if version_str.isdigit() and key_str:
            keys[int(version_str)] = key_str
    return keys


def _fernet(version: int) -> Fernet:
    key = _key_map().get(version)
    if not key:
        raise IntegrationKeyVaultError(
            f"No integration encryption key configured for version {version}"
        )
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise IntegrationKeyVaultError(
            f"Malformed integration encryption key for version {version}"
        ) from exc


def encrypt_key(plaintext: str, version: int = DEFAULT_KEY_VERSION) -> bytes:
    """Encrypt a plaintext secret to a Fernet token (bytes)."""
    if not plaintext:
        raise IntegrationKeyVaultError("Cannot encrypt an empty secret")
    return _fernet(version).encrypt(plaintext.encode())


def decrypt_key(
    ciphertext: bytes | None, version: int = DEFAULT_KEY_VERSION
) -> str | None:
    """Decrypt a Fernet token back to plaintext. NULL ciphertext -> None.

    Raises IntegrationKeyVaultError on wrong key or malformed/tampered token.
    """
    if ciphertext is None:
        return None
    try:
        return _fernet(version).decrypt(bytes(ciphertext)).decode()
    except InvalidToken as exc:
        raise IntegrationKeyVaultError("Failed to decrypt integration secret") from exc


def mask_key(plaintext: str) -> str:
    """Display mask: first 8 + bullets + last 4 (e.g. ``apikey__••••1234``).

    Short secrets (<= 12 chars) cannot show 8+4 without overlap, so only the
    first character is shown. Empty input returns empty.
    """
    if not plaintext:
        return ""
    if len(plaintext) <= 12:
        return plaintext[0] + "••••"
    return f"{plaintext[:8]}••••{plaintext[-4:]}"


def _to_bytea(token: bytes) -> str:
    """Encode bytes for a Postgres BYTEA column over PostgREST (hex format)."""
    return "\\x" + token.hex()


def _from_bytea(value: Any) -> bytes | None:
    """Decode a BYTEA value returned by PostgREST (``\\x`` hex) back to bytes."""
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, str):
        hex_str = value[2:] if value.startswith("\\x") else value
        return bytes.fromhex(hex_str)
    raise IntegrationKeyVaultError("Unexpected access_token_enc wire type")


def _write_audit(db: Any, tenant_id: str, provider: str) -> None:
    """Best-effort audit row. The audit_log table may not exist yet; a missing
    sink must never block the security-critical key save."""
    try:
        db.table("audit_log").insert(
            {
                "tenant_id": tenant_id,
                "action": "integration_key_saved",
                "metadata": {"provider": provider},
            }
        ).execute()
    except Exception:
        logger.warning(
            "audit_log write skipped for integration key save tenant=%s provider=%s",
            tenant_id,
            provider,
            exc_info=True,
        )


def save_integration_key(
    tenant_id: str,
    provider: str,
    plaintext: str,
    metadata: dict | None = None,
    version: int = DEFAULT_KEY_VERSION,
) -> dict:
    """Encrypt and upsert a tenant's integration secret. Writes only the
    encrypted column; never the plaintext ``access_token``. Returns the masked
    display value."""
    token = encrypt_key(plaintext, version)
    meta = dict(metadata or {})
    meta["enc_key_version"] = version
    db = get_service_supabase()
    db.table("integrations").upsert(
        {
            "tenant_id": tenant_id,
            "provider": provider,
            "access_token_enc": _to_bytea(token),
            "metadata": meta,
        },
        on_conflict="tenant_id,provider",
    ).execute()
    _write_audit(db, tenant_id, provider)
    logger.info(
        "integration key saved tenant=%s provider=%s", tenant_id, provider
    )
    return {
        "provider": provider,
        "masked": mask_key(plaintext),
        "enc_key_version": version,
    }


def load_integration_key(tenant_id: str, provider: str) -> str | None:
    """Decrypt and return a tenant's integration secret, or None if absent."""
    db = get_service_supabase()
    res = (
        db.table("integrations")
        .select("access_token_enc, metadata")
        .eq("tenant_id", tenant_id)
        .eq("provider", provider)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return None
    enc = _from_bytea(rows[0].get("access_token_enc"))
    if enc is None:
        return None
    version = (rows[0].get("metadata") or {}).get(
        "enc_key_version", DEFAULT_KEY_VERSION
    )
    plaintext = decrypt_key(enc, version)
    logger.info(
        "integration key loaded tenant=%s provider=%s", tenant_id, provider
    )
    return plaintext


def rotate_key(
    tenant_id: str, provider: str, old_key_version: int, new_key_version: int
) -> dict:
    """Re-encrypt a stored secret from one key version to another."""
    db = get_service_supabase()
    res = (
        db.table("integrations")
        .select("access_token_enc, metadata")
        .eq("tenant_id", tenant_id)
        .eq("provider", provider)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        raise IntegrationKeyVaultError("No integration row to rotate")
    enc = _from_bytea(rows[0].get("access_token_enc"))
    if enc is None:
        raise IntegrationKeyVaultError("No ciphertext to rotate")
    plaintext = decrypt_key(enc, old_key_version)  # raises on wrong old key
    new_token = encrypt_key(plaintext, new_key_version)
    meta = dict(rows[0].get("metadata") or {})
    meta["enc_key_version"] = new_key_version
    db.table("integrations").update(
        {"access_token_enc": _to_bytea(new_token), "metadata": meta}
    ).eq("tenant_id", tenant_id).eq("provider", provider).execute()
    logger.info(
        "integration key rotated tenant=%s provider=%s v%s->v%s",
        tenant_id,
        provider,
        old_key_version,
        new_key_version,
    )
    return {"provider": provider, "enc_key_version": new_key_version}
