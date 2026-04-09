"""Unit tests for backend.services.document_drafting.

These tests stub out the Supabase client and the Managed Agents client.
No network, no database, no API cost.

Focus areas:
  1. Plan gating — free tier must NOT spend on the agent.
  2. Kind/shape validation — reject bad kind, empty line items.
  3. JSON extraction from the agent reply — fenced, bare, prose-wrapped.
  4. File metadata lookup path (we sidestep get_file_content for V1).
  5. Persisted row shape — kind, file_type, file_name, anthropic_file_id,
     draft_metadata.
  6. Safe filename handling — no path traversal.
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.services.document_drafting import (
    DocumentDraftingError,
    _extract_json_from_reply,
    _safe_filename,
    draft_document,
)


class TestExtractJson:
    def test_bare(self):
        assert _extract_json_from_reply('{"file_id": "f_1"}') == {"file_id": "f_1"}

    def test_fenced(self):
        assert _extract_json_from_reply('```json\n{"file_id":"f_1"}\n```') == {
            "file_id": "f_1"
        }

    def test_prose_wrapped(self):
        reply = 'Saved it. {"file_id": "f_2", "file_type": "pdf"} All done.'
        result = _extract_json_from_reply(reply)
        assert result == {"file_id": "f_2", "file_type": "pdf"}

    def test_empty_returns_none(self):
        assert _extract_json_from_reply("") is None

    def test_non_dict_returns_none(self):
        assert _extract_json_from_reply("[1, 2]") is None


class TestSafeFilename:
    def test_strips_path(self):
        assert _safe_filename("/mnt/session/outputs/quote.pdf", "default.pdf") == "quote.pdf"

    def test_strips_backslash_path(self):
        assert _safe_filename(r"C:\evil\haha.xlsx", "default.xlsx") == "haha.xlsx"

    def test_traversal_rejected(self):
        assert _safe_filename("..", "default.pdf") == "default.pdf"
        assert _safe_filename(".", "default.pdf") == "default.pdf"

    def test_empty_returns_default(self):
        assert _safe_filename("", "fallback.docx") == "fallback.docx"

    def test_special_chars_replaced(self):
        result = _safe_filename("Q1 $$$ quote/?.pdf", "x.pdf")
        assert "/" not in result
        assert "?" not in result
        assert "$" not in result

    def test_normal_name_preserved(self):
        assert _safe_filename("acme-quote-2026.docx", "d.docx") == "acme-quote-2026.docx"


def _fake_supabase(tenant: dict, insert_result: dict | None = None):
    db = MagicMock()
    tables: dict[str, MagicMock] = {}

    def _build_tenants():
        tbl = MagicMock()
        tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[tenant] if tenant else []
        )
        return tbl

    def _build_docs():
        tbl = MagicMock()
        returned = [insert_result] if insert_result else []
        tbl.insert.return_value.execute.return_value = MagicMock(data=returned)
        return tbl

    def _side(name):
        if name not in tables:
            if name == "tenants":
                tables[name] = _build_tenants()
            elif name == "documents":
                tables[name] = _build_docs()
            else:
                tables[name] = MagicMock()
        return tables[name]

    db.table.side_effect = _side
    return db


class TestValidation:
    def test_invalid_kind_rejected(self):
        with pytest.raises(DocumentDraftingError, match="invalid kind"):
            draft_document(
                tenant_id="t",
                lead_id=None,
                kind="contract",
                customer={"name": "x"},
                line_items=[{"description": "a", "qty": 1, "unit_price": 1}],
            )

    def test_empty_line_items_rejected(self):
        with pytest.raises(DocumentDraftingError, match="line_items must not be empty"):
            draft_document(
                tenant_id="t",
                lead_id=None,
                kind="quote",
                customer={"name": "x"},
                line_items=[],
            )


class TestPlanGate:
    def test_free_plan_blocked(self):
        tenant = {"id": "t1", "business_name": "Shop", "plan": "free"}
        db = _fake_supabase(tenant)
        with (
            patch("backend.services.document_drafting.get_supabase", return_value=db),
            patch("backend.services.document_drafting.ManagedAgentsClient") as client_cls,
        ):
            with pytest.raises(DocumentDraftingError, match="not eligible"):
                draft_document(
                    tenant_id="t1",
                    lead_id=None,
                    kind="quote",
                    customer={"name": "Bob"},
                    line_items=[{"description": "Widget", "qty": 1, "unit_price": 100}],
                )
        client_cls.assert_not_called()

    def test_missing_tenant_raises(self):
        db = _fake_supabase(None)
        with patch("backend.services.document_drafting.get_supabase", return_value=db):
            with pytest.raises(DocumentDraftingError, match="tenant .* not found"):
                draft_document(
                    tenant_id="nope",
                    lead_id=None,
                    kind="quote",
                    customer={"name": "X"},
                    line_items=[{"description": "A", "qty": 1, "unit_price": 1}],
                )


class TestFullFlow:
    def test_growth_plan_persists_document(self):
        tenant = {
            "id": "t1",
            "business_name": "Acme Services",
            "business_phone": "+15555555555",
            "plan": "growth",
        }
        inserted_row = {
            "id": "doc_abc",
            "title": "Quote for Bob (2026-04-09)",
            "kind": "quote",
            "file_type": "pdf",
            "file_name": "acme-quote.pdf",
            "anthropic_file_id": "file_123",
            "draft_metadata": {"file_size_bytes": 12345, "session_id": "sess_1"},
        }
        db = _fake_supabase(tenant, insert_result=inserted_row)

        # Agent session: single message with file spec, then idle end_turn.
        events = iter([
            {
                "type": "agent.message",
                "id": "sevt_1",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            '```json\n'
                            '{"file_id": "file_123", "file_name": "acme-quote.pdf", '
                            '"file_type": "pdf", "total": 300, "summary": "ok"}\n'
                            '```'
                        ),
                    }
                ],
            },
            {
                "type": "session.status_idle",
                "id": "sevt_2",
                "stop_reason": {"type": "end_turn"},
            },
        ])
        mock_client = MagicMock()
        mock_client.create_session.return_value = {"id": "sess_1"}
        mock_client.stream_events.return_value = events
        mock_client.send_user_message.return_value = None
        # Metadata lookup returns a size — we don't fetch bytes in V1.
        mock_client.get_file_metadata.return_value = {
            "id": "file_123",
            "size_bytes": 12345,
        }

        mock_handle = MagicMock()
        mock_handle.agent_id = "agent_abc"
        mock_handle.environment_id = "env_abc"

        with (
            patch("backend.services.document_drafting.get_supabase", return_value=db),
            patch("backend.services.document_drafting.ManagedAgentsClient", return_value=mock_client),
            patch("backend.services.document_drafting.document_drafter", return_value=mock_handle),
        ):
            result = draft_document(
                tenant_id="t1",
                lead_id="lead_1",
                kind="quote",
                customer={"name": "Bob", "email": "bob@example.com"},
                line_items=[
                    {"description": "Driveway pressure wash", "qty": 1, "unit_price": 300},
                ],
                notes="Residential job",
            )

        assert result["id"] == "doc_abc"

        # Persistence payload shape
        insert_call = db.table("documents").insert.call_args
        row = insert_call.args[0]
        assert row["kind"] == "quote"
        assert row["file_type"] == "pdf"
        assert row["file_name"] == "acme-quote.pdf"
        assert row["anthropic_file_id"] == "file_123"
        assert row["generated_by_agent"] == "document_drafter"
        assert row["tenant_id"] == "t1"
        assert row["lead_id"] == "lead_1"
        assert row["signer_name"] == "Bob"
        assert row["signer_email"] == "bob@example.com"
        assert row["draft_metadata"]["file_size_bytes"] == 12345
        assert row["draft_metadata"]["customer"]["name"] == "Bob"
        assert len(row["draft_metadata"]["line_items"]) == 1
        assert "file_bytes" not in row  # V1 stores nothing inline

        # Get metadata was called; get_file_content was NOT (V1 lazy).
        mock_client.get_file_metadata.assert_called_once_with("file_123")
        mock_client.get_file_content.assert_not_called()

        # Session metadata tags
        session_kwargs = mock_client.create_session.call_args.kwargs
        assert session_kwargs["metadata"]["flow"] == "document_drafting"
        assert session_kwargs["metadata"]["kind"] == "quote"
        assert session_kwargs["metadata"]["tenant_id"] == "t1"

    def test_reply_missing_file_id_raises(self):
        tenant = {"id": "t1", "business_name": "Shop", "plan": "professional"}
        db = _fake_supabase(tenant)

        events = iter([
            {
                "type": "agent.message",
                "id": "sevt_1",
                "content": [{"type": "text", "text": '{"total": 100}'}],
            },
            {
                "type": "session.status_idle",
                "id": "sevt_2",
                "stop_reason": {"type": "end_turn"},
            },
        ])
        mock_client = MagicMock()
        mock_client.create_session.return_value = {"id": "sess_1"}
        mock_client.stream_events.return_value = events

        mock_handle = MagicMock()
        mock_handle.agent_id = "agent_abc"
        mock_handle.environment_id = "env_abc"

        with (
            patch("backend.services.document_drafting.get_supabase", return_value=db),
            patch("backend.services.document_drafting.ManagedAgentsClient", return_value=mock_client),
            patch("backend.services.document_drafting.document_drafter", return_value=mock_handle),
        ):
            with pytest.raises(DocumentDraftingError, match="missing file_id"):
                draft_document(
                    tenant_id="t1",
                    lead_id=None,
                    kind="quote",
                    customer={"name": "X"},
                    line_items=[{"description": "A", "qty": 1, "unit_price": 1}],
                )

    def test_invalid_file_type_raises(self):
        tenant = {"id": "t1", "business_name": "Shop", "plan": "growth"}
        db = _fake_supabase(tenant)

        events = iter([
            {
                "type": "agent.message",
                "id": "sevt_1",
                "content": [
                    {
                        "type": "text",
                        "text": '{"file_id": "f_1", "file_type": "zip", "file_name": "x.zip"}',
                    }
                ],
            },
            {
                "type": "session.status_idle",
                "id": "sevt_2",
                "stop_reason": {"type": "end_turn"},
            },
        ])
        mock_client = MagicMock()
        mock_client.create_session.return_value = {"id": "sess_1"}
        mock_client.stream_events.return_value = events

        mock_handle = MagicMock()
        mock_handle.agent_id = "agent_abc"
        mock_handle.environment_id = "env_abc"

        with (
            patch("backend.services.document_drafting.get_supabase", return_value=db),
            patch("backend.services.document_drafting.ManagedAgentsClient", return_value=mock_client),
            patch("backend.services.document_drafting.document_drafter", return_value=mock_handle),
        ):
            with pytest.raises(DocumentDraftingError, match="invalid file_type"):
                draft_document(
                    tenant_id="t1",
                    lead_id=None,
                    kind="quote",
                    customer={"name": "X"},
                    line_items=[{"description": "A", "qty": 1, "unit_price": 1}],
                )
