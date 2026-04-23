"""App-level encryption for integration API keys.

Uses Fernet (AES-128 in CBC mode with HMAC-SHA256) from the cryptography library.
Key is loaded from INTEGRATIONS_ENC_KEY env var (base64-encoded Fernet key).

CRITICAL: Decryption happens in Python only — the key never touches SQL or pgcrypto.
This prevents the key from appearing in Postgres logs, pg_stat_statements, or audit trails.

Usage:
    ciphertext = encrypt_key("sk_live_abc123")
    # store ciphertext in integrations.access_token_enc (BYTEA column)

    plaintext = decrypt_key(ciphertext)
    # raises cryptography.fernet.InvalidToken on wrong key or corruption

Generate a key for Railway:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import logging
import os

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Load and validate INTEGRATIONS_ENC_KEY from env.

    Raises RuntimeError clearly when key is missing so callers (and tests) can
    detect misconfiguration immediately rather than discovering it at encrypt time.
    """
    key = os.environ.get("INTEGRATIONS_ENC_KEY")
    if not key:
        raise RuntimeError(
            "INTEGRATIONS_ENC_KEY not set — cannot encrypt/decrypt integration keys. "
            "Set this env var in Railway with a valid Fernet key. "
            'Generate one: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    raw = key.encode() if isinstance(key, str) else key
    return Fernet(raw)


def encrypt_key(plaintext: str) -> bytes:
    """Encrypt an API key. Returns ciphertext bytes for storage in access_token_enc.

    Args:
        plaintext: Raw API key string (e.g. "sk_live_abc123...")

    Returns:
        Fernet ciphertext as bytes, suitable for BYTEA column storage.

    Raises:
        RuntimeError: INTEGRATIONS_ENC_KEY env var is not set.
    """
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8"))


def decrypt_key(ciphertext: bytes) -> str:
    """Decrypt stored ciphertext back to plaintext API key.

    Args:
        ciphertext: Bytes previously returned by encrypt_key().

    Returns:
        Plaintext API key string.

    Raises:
        RuntimeError: INTEGRATIONS_ENC_KEY env var is not set.
        InvalidToken: Wrong key, corrupted bytes, or tampered data.
    """
    f = _get_fernet()
    return f.decrypt(ciphertext).decode("utf-8")


def mask_key(plaintext: str) -> str:
    """Return masked version of API key for safe display in UI.

    Format: first 8 chars + bullet string + last 4 chars.
    For keys shorter than 16 chars: bullet string + last 4 chars only.

    Args:
        plaintext: Raw API key string.

    Returns:
        Masked string safe for logging and UI display.
    """
    if len(plaintext) < 16:
        return "••••" + plaintext[-4:]
    return plaintext[:8] + "•••••" + plaintext[-4:]


def is_test_key(api_key: str, env: str = "production") -> bool:
    """Detect if a Stripe test key is being used in a production environment.

    Only Stripe test keys (sk_test_ prefix) in the production environment are
    flagged. Staging and development environments are expected to use test keys.

    Args:
        api_key: The API key string to inspect.
        env: Environment name. Only "production" triggers the flag.

    Returns:
        True if a Stripe test key is detected in production; False otherwise.
    """
    return env == "production" and api_key.startswith("sk_test_")
