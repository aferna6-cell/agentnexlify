"""Cross-cutting tenant isolation tests for critical endpoints."""

import pytest
from backend.tests.conftest import _make_auth_token


# Endpoints that take {tenant_id} in path — must reject mismatched JWT
# Only include endpoints we've verified exist and enforce tenant checks
TENANT_ENDPOINTS = [
    ("GET", "/api/v1/leads/{tid}"),
    ("GET", "/api/v1/clients/{tid}"),
    ("GET", "/api/v1/appointments/{tid}"),
    ("GET", "/api/v1/invoices/{tid}"),
    ("GET", "/api/v1/documents/{tid}"),
    ("GET", "/api/v1/forms/{tid}"),
    ("GET", "/api/v1/bids/{tid}"),
    ("GET", "/api/v1/calls/{tid}"),
    ("GET", "/api/v1/reviews/{tid}"),
    ("GET", "/api/v1/pipeline/{tid}/stages"),
    ("GET", "/api/v1/smart-lists/{tid}"),
]


class TestCrossTenantAccess:
    """Verify all major endpoints reject cross-tenant access."""

    @pytest.mark.parametrize("method,path_template", TENANT_ENDPOINTS)
    def test_cross_tenant_blocked(self, client, method, path_template):
        """Accessing 00000000-0000-0000-0000-00000000000b data with 00000000-0000-0000-0000-00000000000a token returns 403."""
        token_a = _make_auth_token("00000000-0000-0000-0000-00000000000a")
        path = path_template.replace("{tid}", "00000000-0000-0000-0000-00000000000b")

        resp = client.request(
            method, path,
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 403, f"{method} {path} returned {resp.status_code}, expected 403"

    def test_unauthenticated_access_blocked(self, client):
        """Key endpoints reject unauthenticated requests (401 or 422)."""
        endpoints = [
            "/api/v1/auth/dashboard/any-tenant",
            "/api/v1/auth/faq/any-tenant",
        ]
        for endpoint in endpoints:
            resp = client.get(endpoint)
            assert resp.status_code in (401, 403, 422), f"{endpoint} accessible without auth!"
