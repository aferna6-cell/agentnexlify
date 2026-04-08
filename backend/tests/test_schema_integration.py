"""Integration tests: verify code schema assumptions match live Supabase.

These tests query the actual Supabase database to verify that columns
referenced in code actually exist. Run with real credentials:

    SUPABASE_URL=... SUPABASE_KEY=... python3 -m pytest backend/tests/test_schema_integration.py -v

Skip automatically when Supabase credentials are not available.
"""

import os
import pytest

# Skip entire module if no Supabase credentials
pytestmark = pytest.mark.skipif(
    not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_KEY"),
    reason="SUPABASE_URL/SUPABASE_KEY not set — skipping integration tests",
)


@pytest.fixture(scope="module")
def db():
    """Real Supabase client for schema verification."""
    from backend.models.database import get_supabase
    return get_supabase()


@pytest.fixture(scope="module")
def schema_columns(db):
    """Fetch all columns from information_schema for the public schema."""
    result = db.rpc("get_schema_columns", {}).execute()
    if result.data:
        return result.data
    # Fallback: query information_schema directly
    # This might not work with RLS, so we use a simpler approach
    return None


# --- Critical Column Existence Tests ---

class TestLeadsSchema:
    """Verify leads table matches code assumptions."""

    def test_leads_has_client_id(self, db):
        """leads table uses client_id, NOT tenant_id."""
        result = db.table("leads").select("client_id").limit(0).execute()
        # If this doesn't raise, the column exists
        assert result is not None

    def test_leads_has_status(self, db):
        """leads table uses status, NOT lead_stage."""
        result = db.table("leads").select("status").limit(0).execute()
        assert result is not None

    def test_leads_has_areas_of_interest(self, db):
        """leads table uses areas_of_interest, NOT service_interest."""
        result = db.table("leads").select("areas_of_interest").limit(0).execute()
        assert result is not None

    def test_leads_has_lead_score(self, db):
        """leads.lead_score column exists."""
        result = db.table("leads").select("lead_score").limit(0).execute()
        assert result is not None

    def test_leads_has_tags(self, db):
        """leads.tags column exists (TEXT[])."""
        result = db.table("leads").select("tags").limit(0).execute()
        assert result is not None


class TestConversationsSchema:
    """Verify conversations table matches code assumptions."""

    def test_conversations_has_client_id(self, db):
        """conversations uses client_id, NOT tenant_id."""
        result = db.table("conversations").select("client_id").limit(0).execute()
        assert result is not None

    def test_conversations_has_session_id(self, db):
        result = db.table("conversations").select("session_id").limit(0).execute()
        assert result is not None

    def test_conversations_has_tags(self, db):
        result = db.table("conversations").select("tags").limit(0).execute()
        assert result is not None


class TestAppointmentsSchema:
    """Verify appointments table matches code assumptions."""

    def test_appointments_has_tenant_id(self, db):
        result = db.table("appointments").select("tenant_id").limit(0).execute()
        assert result is not None

    def test_appointments_has_start_end_time(self, db):
        result = db.table("appointments").select("start_time, end_time").limit(0).execute()
        assert result is not None

    def test_appointments_has_status(self, db):
        result = db.table("appointments").select("status").limit(0).execute()
        assert result is not None


class TestDocumentsSchema:
    """Verify documents table matches code assumptions."""

    def test_documents_has_signing_token(self, db):
        result = db.table("documents").select("signing_token").limit(0).execute()
        assert result is not None

    def test_documents_has_signature_data(self, db):
        result = db.table("documents").select("signature_data").limit(0).execute()
        assert result is not None


class TestInvoicesSchema:
    """Verify invoices table matches code assumptions."""

    def test_invoices_has_tenant_id(self, db):
        result = db.table("invoices").select("tenant_id").limit(0).execute()
        assert result is not None

    def test_invoices_has_items_json(self, db):
        result = db.table("invoices").select("items_json").limit(0).execute()
        assert result is not None

    def test_invoices_has_amount_paid(self, db):
        result = db.table("invoices").select("amount_paid").limit(0).execute()
        assert result is not None


class TestTenantScopeMapping:
    """Verify tenant_scope.py column overrides match reality."""

    def test_leads_uses_client_id(self, db):
        """tenant_scope maps leads → client_id. Verify column exists."""
        from backend.services.tenant_scope import tenant_scope_column
        col = tenant_scope_column("leads")
        assert col == "client_id"
        result = db.table("leads").select(col).limit(0).execute()
        assert result is not None

    def test_conversations_uses_client_id(self, db):
        """tenant_scope maps conversations → client_id. Verify column exists."""
        from backend.services.tenant_scope import tenant_scope_column
        col = tenant_scope_column("conversations")
        assert col == "client_id"
        result = db.table("conversations").select(col).limit(0).execute()
        assert result is not None

    def test_default_tables_use_tenant_id(self, db):
        """Other tables default to tenant_id."""
        from backend.services.tenant_scope import tenant_scope_column
        for table in ["appointments", "invoices", "documents", "chat_messages", "faq_entries"]:
            col = tenant_scope_column(table)
            assert col == "tenant_id", f"{table} should use tenant_id, got {col}"
            result = db.table(table).select(col).limit(0).execute()
            assert result is not None
