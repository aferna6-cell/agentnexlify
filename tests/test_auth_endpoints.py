"""Tests for authentication endpoints — signup, login, password reset, and checkout.

These use FastAPI's TestClient with mocked Supabase to test
the register and login flows without hitting the real database.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_auth_token(
    tenant_id: str = "tenant-001",
    role: str = "owner",
    secret: str = "test-secret-key-for-jwt",
):
    from jose import jwt

    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": "owner@example.com",
        "plan": "free",
        "business_name": "Test Business",
        "role": role,
        "is_team_member": False,
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def test_client(mock_settings):
    """Create a FastAPI TestClient with mocked Supabase everywhere."""
    mock_settings.sentry_dsn = None
    mock_settings.supabase_service_key = "fake-key"

    # Patch get_supabase in every module that imports it
    db_mock = MagicMock()
    patches = [
        patch("backend.models.database.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.get_service_supabase", return_value=db_mock),
        patch("backend.routers.auth.settings", mock_settings),
        # billing endpoints moved to auth_billing (2026-06-11 god-file split)
        patch("backend.routers.auth_billing.get_service_supabase", return_value=db_mock),
        patch("backend.routers.auth_billing.settings", mock_settings),
        patch(
            "backend.services.fraud_guard.get_service_supabase", return_value=db_mock
        ),
        patch("backend.routers.widget_chat.get_service_supabase", return_value=db_mock),
        patch(
            "backend.routers.widget_config.get_service_supabase", return_value=db_mock
        ),
        patch("backend.routers.widget_lead.get_service_supabase", return_value=db_mock),
        patch(
            "backend.routers.widget_booking.get_service_supabase", return_value=db_mock
        ),
        patch(
            "backend.routers.widget_chat_helpers.get_service_supabase",
            return_value=db_mock,
        ),
        patch(
            "backend.services.industry_faqs._get_service_supabase",
            return_value=db_mock,
        ),
        patch(
            "backend.services.widget_config_service._get_service_supabase",
            return_value=db_mock,
        ),
        patch(
            "backend.services.faq_service._get_service_supabase",
            return_value=db_mock,
        ),
        patch(
            "backend.services.conversations_service._get_service_supabase",
            return_value=db_mock,
        ),
        patch(
            "backend.services.dashboard_service._get_service_supabase",
            return_value=db_mock,
        ),
    ]
    for p in patches:
        p.start()

    from backend.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    yield client, db_mock

    for p in patches:
        p.stop()


def _setup_table_mock(db_mock, table_responses):
    """Configure db_mock.table() to return different data per table name.

    table_responses: dict of {table_name: [list of response dicts]}
    Supports chained calls: .select().eq().limit().execute()
    """
    call_counts = {}

    def mock_table(name):
        call_counts.setdefault(name, 0)
        call_counts[name] += 1

        table = MagicMock()
        data = table_responses.get(name, [])

        # If data is a list of lists, pop the first one each call (multi-call support)
        if data and isinstance(data[0], list):
            idx = min(call_counts[name] - 1, len(data) - 1)
            current_data = data[idx]
        else:
            current_data = data

        # Make all chainable methods return the same mock
        for method in [
            "select",
            "insert",
            "update",
            "delete",
            "eq",
            "neq",
            "gte",
            "lte",
            "gt",
            "lt",
            "limit",
            "order",
            "ilike",
            "in_",
            "is_",
            "or_",
            "contains",
        ]:
            getattr(table, method).return_value = table

        # Execute returns the data
        result = MagicMock()
        result.data = current_data
        result.count = len(current_data) if current_data else 0
        table.execute.return_value = result

        return table

    db_mock.table = mock_table


class TestRegister:
    """Test the POST /api/v1/auth/register endpoint."""

    def test_duplicate_email_returns_409(self, test_client):
        """Signing up with an existing email should return 409."""
        client, db_mock = test_client

        _setup_table_mock(
            db_mock,
            {
                "tenants": [{"id": "existing-tenant"}],  # duplicate check finds a match
            },
        )

        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "existing@example.com",
                "password": "TestPass123!",
                "business_name": "Test Business",
                "owner_name": "Test Owner",
                "industry": "plumbing",
                "city": "New York",
            },
        )
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()

    def test_successful_register(self, test_client):
        """New email should create tenant and return 200 with token."""
        client, db_mock = test_client

        # First call (duplicate check) returns empty, second call (insert) returns new tenant
        _setup_table_mock(
            db_mock,
            {
                "tenants": [
                    [],  # first call: no duplicate
                    [
                        {
                            "id": "new-tenant-001",
                            "business_name": "Test Biz",
                            "owner_email": "new@example.com",
                            "plan": "free",
                        }
                    ],  # second call: insert result
                ],
                "widget_configs": [{"id": "wc-001"}],  # widget config insert
            },
        )

        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@example.com",
                "password": "TestPass123!",
                "business_name": "Test Biz",
                "owner_name": "Test Owner",
                "industry": "plumbing",
                "city": "New York",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["tenant_id"] == "new-tenant-001"
        assert "api_key" in data
        assert data["api_key"].startswith("anx_")


class TestLogin:
    """Test the POST /api/v1/auth/login endpoint."""

    def test_wrong_email_returns_401(self, test_client):
        """Login with non-existent email should return 401."""
        client, db_mock = test_client

        _setup_table_mock(
            db_mock,
            {
                "tenants": [],
                "team_members": [],
            },
        )

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPass123",
            },
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_wrong_password_returns_401(self, test_client):
        """Login with correct email but wrong password should return 401."""
        client, db_mock = test_client
        import bcrypt

        correct_hash = bcrypt.hashpw(b"CorrectPass123", bcrypt.gensalt()).decode()

        _setup_table_mock(
            db_mock,
            {
                "tenants": [
                    {
                        "id": "tenant-001",
                        "password_hash": correct_hash,
                        "business_name": "Test Biz",
                        "plan": "free",
                    }
                ],
            },
        )

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPass123",
            },
        )
        assert response.status_code == 401

    def test_successful_login(self, test_client):
        """Login with correct credentials should return token."""
        client, db_mock = test_client
        import bcrypt

        password = "CorrectPass123!"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        _setup_table_mock(
            db_mock,
            {
                "tenants": [
                    {
                        "id": "tenant-001",
                        "password_hash": hashed,
                        "business_name": "Test Business",
                        "plan": "growth",
                    }
                ],
            },
        )

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": password,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["tenant_id"] == "tenant-001"
        assert data["business_name"] == "Test Business"
        assert data["plan"] == "growth"

    def test_no_password_hash_returns_401(self, test_client):
        """Tenant without password_hash (legacy) should get 401."""
        client, db_mock = test_client

        _setup_table_mock(
            db_mock,
            {
                "tenants": [
                    {
                        "id": "tenant-001",
                        "password_hash": None,
                        "business_name": "Legacy Biz",
                        "plan": "free",
                    }
                ],
            },
        )

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "legacy@example.com",
                "password": "anything",
            },
        )
        assert response.status_code == 401


class TestPasswordReset:
    """Test forgot/reset password flows."""

    @patch(
        "backend.routers.auth.secrets.token_urlsafe", return_value="fixed-reset-token"
    )
    @patch("backend.routers.auth.send_email", new_callable=AsyncMock)
    def test_forgot_password_existing_email_sends_reset_link(
        self, mock_send_email, _mock_token, test_client
    ):
        client, db_mock = test_client

        _setup_table_mock(
            db_mock,
            {
                "tenants": [
                    [
                        {
                            "id": "tenant-001",
                            "owner_email": "owner@example.com",
                            "owner_name": "Owner",
                            "business_name": "Test Business",
                        }
                    ],
                    [],
                ],
            },
        )

        response = client.post(
            "/api/v1/auth/forgot-password", json={"email": "owner@example.com"}
        )

        assert response.status_code == 200
        assert "reset link has been sent" in response.json()["message"].lower()
        mock_send_email.assert_awaited_once()
        kwargs = mock_send_email.await_args.kwargs
        assert kwargs["to"] == "owner@example.com"
        assert "fixed-reset-token" in kwargs["body_html"]

    @patch("backend.routers.auth.send_email", new_callable=AsyncMock)
    def test_forgot_password_unknown_email_returns_generic_message(
        self, mock_send_email, test_client
    ):
        client, db_mock = test_client

        _setup_table_mock(db_mock, {"tenants": []})

        response = client.post(
            "/api/v1/auth/forgot-password", json={"email": "missing@example.com"}
        )

        assert response.status_code == 200
        assert "reset link has been sent" in response.json()["message"].lower()
        mock_send_email.assert_not_awaited()

    def test_reset_password_invalid_token_returns_400(self, test_client):
        client, db_mock = test_client

        _setup_table_mock(db_mock, {"tenants": []})

        response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "bad-token", "password": "NewPassword123!"},
        )

        assert response.status_code == 400
        assert "invalid or expired" in response.json()["detail"].lower()

    def test_reset_password_success_updates_hash_and_clears_token(self, test_client):
        client, db_mock = test_client

        tenant_table = MagicMock()
        for method in ["select", "update", "eq", "limit"]:
            getattr(tenant_table, method).return_value = tenant_table
        tenant_table.execute.side_effect = [
            MagicMock(
                data=[
                    {
                        "id": "tenant-001",
                        "reset_token_expires": (
                            datetime.now(timezone.utc) + timedelta(hours=1)
                        ).isoformat(),
                    }
                ]
            ),
            MagicMock(data=[]),
        ]

        def mock_table(name):
            assert name == "tenants"
            return tenant_table

        db_mock.table = mock_table

        response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "valid-token", "password": "NewPassword123!"},
        )

        assert response.status_code == 200
        assert "successfully" in response.json()["message"].lower()

        update_payload = tenant_table.update.call_args[0][0]
        assert update_payload["reset_token"] is None
        assert update_payload["reset_token_expires"] is None
        assert update_payload["password_hash"] != "NewPassword123!"
        assert update_payload["password_hash"]


class TestBillingCheckout:
    """Test Stripe checkout session creation from the auth router."""

    @patch("backend.routers.auth_billing.ensure_plan_prices_configured")
    @patch("backend.routers.auth_billing.ensure_stripe_configured")
    @patch("backend.routers.auth_billing.stripe.checkout.Session.create")
    @patch("backend.routers.auth_billing.get_or_create_customer")
    def test_billing_checkout_returns_checkout_url(
        self,
        mock_customer,
        mock_create_session,
        mock_ensure_stripe,
        mock_ensure_prices,
        test_client,
    ):
        client, db_mock = test_client
        token = _make_auth_token()

        _setup_table_mock(
            db_mock,
            {
                "tenants": [
                    {
                        "id": "tenant-001",
                        "owner_email": "owner@example.com",
                        "business_name": "Test Business",
                    }
                ],
            },
        )

        mock_ensure_stripe.return_value = None
        mock_ensure_prices.return_value = {"monthly": "price_growth_monthly"}
        mock_customer.return_value = MagicMock(id="cus_123")
        mock_create_session.return_value = MagicMock(
            url="https://checkout.stripe.test/session_123"
        )

        response = client.post(
            "/api/v1/auth/billing/checkout",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan": "growth"},
        )

        assert response.status_code == 200
        assert (
            response.json()["checkout_url"]
            == "https://checkout.stripe.test/session_123"
        )
        mock_create_session.assert_called_once()

    def test_billing_checkout_rejects_invalid_plan(self, test_client):
        client, _db_mock = test_client
        token = _make_auth_token()

        response = client.post(
            "/api/v1/auth/billing/checkout",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan": "invalid"},
        )

        assert response.status_code == 400
        assert "invalid plan" in response.json()["detail"].lower()


class TestGoogleOAuth:
    """Test Google OAuth helper endpoints."""

    def test_google_auth_url_returns_google_redirect(self, test_client, mock_settings):
        client, _db_mock = test_client
        mock_settings.google_client_id = "google-client-id"
        mock_settings.google_client_secret = "google-client-secret"
        mock_settings.api_url = "https://api.example.com"

        response = client.get("/api/v1/auth/google/url?mode=signup&plan=growth")

        assert response.status_code == 200
        auth_url = response.json()["auth_url"]
        parsed = urlparse(auth_url)
        params = parse_qs(parsed.query)
        assert parsed.netloc == "accounts.google.com"
        assert params["client_id"] == ["google-client-id"]
        assert params["redirect_uri"] == [
            "https://api.example.com/api/v1/auth/google/callback"
        ]
        assert params["scope"] == ["openid email profile"]
        assert "state" in params

    @patch("backend.routers.auth.httpx.AsyncClient")
    def test_google_callback_existing_owner_redirects_to_dashboard(
        self, mock_async_client, test_client, mock_settings
    ):
        client, db_mock = test_client
        mock_settings.google_client_id = "google-client-id"
        mock_settings.google_client_secret = "google-client-secret"
        mock_settings.api_url = "https://api.example.com"
        mock_settings.frontend_url = "https://app.example.com"

        from backend.routers.auth import _encode_google_state

        state = _encode_google_state("login")

        _setup_table_mock(
            db_mock,
            {
                "tenants": [
                    {
                        "id": "tenant-001",
                        "business_name": "Test Business",
                        "plan": "growth",
                        "business_type": "plumbing",
                    }
                ],
            },
        )

        token_response = MagicMock()
        token_response.raise_for_status.return_value = None
        token_response.json.return_value = {"access_token": "google-access-token"}

        userinfo_response = MagicMock()
        userinfo_response.raise_for_status.return_value = None
        userinfo_response.json.return_value = {
            "email": "owner@example.com",
            "name": "Owner Example",
            "email_verified": True,
        }

        http_client = AsyncMock()
        http_client.post.return_value = token_response
        http_client.get.return_value = userinfo_response
        mock_async_client.return_value.__aenter__.return_value = http_client

        response = client.get(
            f"/api/v1/auth/google/callback?code=test-code&state={state}",
            follow_redirects=False,
        )

        assert response.status_code in {302, 307}
        location = response.headers["location"]
        assert location.startswith("https://app.example.com/auth/callback#")
        assert "tenant_id=tenant-001" in location
        assert "token=" in location

    @patch("backend.routers.auth.send_email", new_callable=AsyncMock)
    def test_google_register_creates_account(self, mock_send_email, test_client):
        client, db_mock = test_client

        from backend.routers.auth import _encode_google_setup_token

        setup_token = _encode_google_setup_token(
            email="owner@example.com",
            owner_name="Owner Example",
            plan="growth",
        )

        _setup_table_mock(
            db_mock,
            {
                "tenants": [
                    [],
                    [
                        {
                            "id": "tenant-google-001",
                            "business_name": "Google Biz",
                            "owner_email": "owner@example.com",
                            "plan": "free",
                        }
                    ],
                ],
                "widget_configs": [{"id": "wc-001"}],
            },
        )

        response = client.post(
            "/api/v1/auth/google-register",
            json={
                "setup_token": setup_token,
                "business_name": "Google Biz",
                "industry": "hvac",
                "city": "Austin",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-google-001"
        assert data["api_key"].startswith("anx_")
        assert data["token"]
        mock_send_email.assert_awaited_once()
