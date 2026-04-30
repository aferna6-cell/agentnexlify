"""API key authentication service for Zapier CRM export integration.

Handles secure API key generation, hashing (bcrypt cost 12), and
prefix-based lookup (short-circuit before bcrypt verify).

Table: tenant_api_keys (see migrations/110_tenant_api_keys.sql)
  - client_id (FK tenants.id) — NOT tenant_id per CLAUDE.md Rule 1
  - key_hash: bcrypt hash (cost 12)
  - key_prefix: first 8 chars for index lookup

Key format: "zap_<32-char-urlsafe-token>"
  e.g. zap_aB3dEfGhIjKlMnOpQrStUvWxYz012345
"""

import logging
import secrets

import bcrypt

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

_BCRYPT_ROUNDS = 12
_KEY_PREFIX_LEN = 8
_KEY_PREFIX = "zap_"

# Tiers allowed to use Zapier integration
_ALLOWED_PLANS = {"growth", "autopilot", "professional", "enterprise"}


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new Zapier API key.

    Returns a 3-tuple of (raw_key, key_hash, key_prefix):
      raw_key   — the full plaintext key shown ONCE to the user
      key_hash  — bcrypt hash (cost 12) for storage
      key_prefix — first 8 chars of raw_key for indexed prefix lookup
    """
    token = secrets.token_urlsafe(32)
    raw_key = f"{_KEY_PREFIX}{token}"
    key_prefix = raw_key[:_KEY_PREFIX_LEN]
    key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()
    return raw_key, key_hash, key_prefix


def validate_api_key(raw_key: str) -> dict | None:
    """Validate an API key and return the key row if valid, else None.

    Uses prefix-based lookup to narrow candidates before bcrypt verify.
    Also checks that the key is not revoked.

    Returns the full tenant_api_keys row dict on success, None on failure.
    Does NOT perform tier gating here — the router dependency does that.
    """
    if not raw_key or len(raw_key) < _KEY_PREFIX_LEN:
        return None

    key_prefix = raw_key[:_KEY_PREFIX_LEN]
    db = get_service_supabase()

    try:
        result = (
            db.table("tenant_api_keys")
            .select(
                "id, client_id, key_hash, key_prefix, name, last_used_at, revoked_at, rate_limit_rpm"
            )
            .eq("key_prefix", key_prefix)
            .is_("revoked_at", "null")
            .execute()
        )
    except Exception:
        logger.exception("DB error during API key prefix lookup")
        return None

    for row in result.data or []:
        stored_hash = row.get("key_hash", "")
        try:
            if bcrypt.checkpw(raw_key.encode(), stored_hash.encode()):
                return row
        except Exception:
            logger.warning("bcrypt verify error for key prefix %s", key_prefix)
            continue

    return None


def touch_last_used(key_id: str) -> None:
    """Update last_used_at timestamp for a key (best-effort, no raise)."""
    from datetime import datetime, timezone

    db = get_service_supabase()
    try:
        db.table("tenant_api_keys").update(
            {"last_used_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", key_id).execute()
    except Exception:
        logger.warning("Failed to touch last_used_at for key %s", key_id)
