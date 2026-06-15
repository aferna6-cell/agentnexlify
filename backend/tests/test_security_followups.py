"""Security/drift follow-ups (2026-06-15 launch-readiness audit).

Covers:
- M2  admin secret does not fall back to the JWT signing key in production.
- L1  rate-limit XFF fallback uses the trusted right-most entry.
- admin MRR plan prices match the two-plan model.
- audit_log best-effort write shape (table created in migration 151).
"""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")


class _FakeReq:
    """Minimal Request stand-in for get_client_id_key (no body, no api_key)."""

    def __init__(self, xff=None, client_host=None):
        self.query_params = {}
        self.state = type("S", (), {})()  # no _body attr
        self.client = type("C", (), {"host": client_host})() if client_host else None
        self.headers = {"x-forwarded-for": xff} if xff else {}


# --- L1: XFF fallback uses the right-most (trusted edge) entry ---------------


def test_rate_key_uses_rightmost_xff_when_no_client():
    from backend.middleware.rate_limit import get_client_id_key

    req = _FakeReq(xff="1.1.1.1, 2.2.2.2, 3.3.3.3", client_host=None)
    assert get_client_id_key(req) == "3.3.3.3"


def test_rate_key_prefers_client_host_over_xff():
    from backend.middleware.rate_limit import get_client_id_key

    req = _FakeReq(xff="1.1.1.1, 2.2.2.2", client_host="9.9.9.9")
    assert get_client_id_key(req) == "9.9.9.9"


# --- M2: admin secret no fallback in production ------------------------------


def test_admin_secret_rejects_fallback_in_production():
    from backend.routers import admin_analytics

    with patch.object(admin_analytics.settings, "admin_api_secret_key", ""), patch.object(
        admin_analytics.settings, "api_secret_key", "shared-jwt-key"
    ), patch.object(admin_analytics, "is_production", return_value=True):
        assert admin_analytics._admin_secret() == ""


def test_admin_secret_falls_back_in_dev_only():
    from backend.routers import admin_analytics

    with patch.object(admin_analytics.settings, "admin_api_secret_key", ""), patch.object(
        admin_analytics.settings, "api_secret_key", "shared-jwt-key"
    ), patch.object(admin_analytics, "is_production", return_value=False):
        assert admin_analytics._admin_secret() == "shared-jwt-key"


def test_admin_secret_uses_distinct_value_when_set():
    from backend.routers import admin_analytics

    with patch.object(admin_analytics.settings, "admin_api_secret_key", "distinct-admin"), patch.object(
        admin_analytics, "is_production", return_value=True
    ):
        assert admin_analytics._admin_secret() == "distinct-admin"


def test_admin_mrr_prices_match_two_plan_model():
    from backend.routers import admin_analytics

    assert admin_analytics.PLAN_PRICE_CENTS == {"chatbot": 1999, "agent_os": 9999}


# --- audit_log best-effort write --------------------------------------------


def test_write_audit_inserts_expected_shape():
    from backend.services import integration_key_vault as vault

    db = MagicMock()
    vault._write_audit(db, "tenant-1", "stripe")
    payload = db.table.return_value.insert.call_args.args[0]
    assert payload["action"] == "integration_key_saved"
    assert payload["tenant_id"] == "tenant-1"
    assert payload["metadata"]["provider"] == "stripe"


def test_write_audit_never_raises_on_db_error():
    from backend.services import integration_key_vault as vault

    db = MagicMock()
    db.table.side_effect = RuntimeError("audit_log missing")
    # Must not raise — a missing audit sink can't block the key save.
    vault._write_audit(db, "tenant-1", "twilio")
