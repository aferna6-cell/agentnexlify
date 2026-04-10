"""Unit tests for backend.services.document_drafting.

These tests stub out the Supabase client and the Managed Agents client.
No network, no database, no API cost.

Focus areas:
  1. Plan gating — free tier must NOT spend on the agent.
  2. Kind/shape validation — reject bad kind, empty line items.
  3. JSON extraction from the agent reply — fenced, bare, prose-wrapped.
  4. Base64 contract: decode, magic-byte validation, whitespace tolerance.
  5. Persisted row shape — file_bytes hex escape, metadata with
     redacted content_base64.
  6. Safe filename handling — no path traversal.
"""

import base64
import zlib
from unittest.mock import MagicMock, patch

import pytest

from backend.services.document_drafting import (
    DocumentDraftingError,
    _extract_json_from_reply,
    _safe_filename,
    draft_document,
)


# A minimal real DOCX (ZIP archive) for tests — just needs the PK magic
# header for the magic-byte validator to pass.
_FAKE_DOCX_BYTES = b"PK\x03\x04" + b"minimal docx body for testing only"
_FAKE_DOCX_B64 = base64.b64encode(_FAKE_DOCX_BYTES).decode("ascii")
_FAKE_PDF_BYTES = b"%PDF-1.4\n%fake pdf body for testing only"
_FAKE_PDF_B64 = base64.b64encode(_FAKE_PDF_BYTES).decode("ascii")


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
            patch("backend.services.document_drafting.get_service_supabase", return_value=db),
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
        with patch("backend.services.document_drafting.get_service_supabase", return_value=db):
            with pytest.raises(DocumentDraftingError, match="tenant .* not found"):
                draft_document(
                    tenant_id="nope",
                    lead_id=None,
                    kind="quote",
                    customer={"name": "X"},
                    line_items=[{"description": "A", "qty": 1, "unit_price": 1}],
                )


def _mock_agent_session(
    reply_text: str,
    handle_agent_id: str = "agent_abc",
    tool_result_text: str | None = None,
):
    """Build a mock Managed Agents client + handle for drafter tests.

    If ``tool_result_text`` is provided, a synthetic ``agent.tool_result``
    event carrying that text is emitted BEFORE the final ``agent.message``.
    Use this to simulate the server-side ``base64 -w0`` tool output so the
    drafter code can pluck the authoritative payload from the stream.
    """
    events_list: list[dict] = []
    if tool_result_text is not None:
        events_list.append(
            {
                "type": "agent.tool_result",
                "id": "sevt_tr_1",
                "content": [{"type": "text", "text": tool_result_text}],
            }
        )
    events_list.extend(
        [
            {
                "type": "agent.message",
                "id": "sevt_1",
                "content": [{"type": "text", "text": reply_text}],
            },
            {
                "type": "session.status_idle",
                "id": "sevt_2",
                "stop_reason": {"type": "end_turn"},
            },
        ]
    )
    events = iter(events_list)
    mock_client = MagicMock()
    mock_client.create_session.return_value = {"id": "sess_1"}
    mock_client.stream_events.return_value = events
    mock_client.send_user_message.return_value = None

    mock_handle = MagicMock()
    mock_handle.agent_id = handle_agent_id
    mock_handle.environment_id = "env_abc"
    return mock_client, mock_handle


class TestFullFlow:
    def test_growth_plan_persists_docx_with_bytes(self):
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
            "file_type": "docx",
            "file_name": "acme-quote.docx",
            "draft_metadata": {"file_size_bytes": len(_FAKE_DOCX_BYTES), "session_id": "sess_1"},
        }
        db = _fake_supabase(tenant, insert_result=inserted_row)

        reply = (
            "```json\n"
            '{"file_name": "acme-quote.docx", "file_type": "docx", '
            '"total": 300, "summary": "ok", '
            f'"content_base64": "{_FAKE_DOCX_B64}"}}\n'
            "```"
        )
        mock_client, mock_handle = _mock_agent_session(reply)

        with (
            patch("backend.services.document_drafting.get_service_supabase", return_value=db),
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
        assert row["file_type"] == "docx"
        assert row["file_name"] == "acme-quote.docx"
        assert row["generated_by_agent"] == "document_drafter"
        assert row["tenant_id"] == "t1"
        assert row["lead_id"] == "lead_1"
        assert row["signer_name"] == "Bob"
        assert row["signer_email"] == "bob@example.com"

        # file_bytes stored as \x<hex>
        assert row["file_bytes"].startswith("\\x")
        assert row["file_bytes"] == "\\x" + _FAKE_DOCX_BYTES.hex()

        # content_base64 redacted from stored spec (don't double-store)
        assert "content_base64" not in row["draft_metadata"]["spec"]
        assert row["draft_metadata"]["file_size_bytes"] == len(_FAKE_DOCX_BYTES)

        # Files API should NOT have been touched — we now use inline bytes.
        mock_client.get_file_metadata.assert_not_called()
        mock_client.get_file_content.assert_not_called()

    def test_pdf_magic_bytes_accepted(self):
        tenant = {"id": "t1", "business_name": "Shop", "plan": "professional"}
        inserted = {"id": "doc_pdf"}
        db = _fake_supabase(tenant, insert_result=inserted)

        reply = (
            '{"file_name": "proposal.pdf", "file_type": "pdf", '
            '"total": 1000, "summary": "ok", '
            f'"content_base64": "{_FAKE_PDF_B64}"}}'
        )
        mock_client, mock_handle = _mock_agent_session(reply)

        with (
            patch("backend.services.document_drafting.get_service_supabase", return_value=db),
            patch("backend.services.document_drafting.ManagedAgentsClient", return_value=mock_client),
            patch("backend.services.document_drafting.document_drafter", return_value=mock_handle),
        ):
            result = draft_document(
                tenant_id="t1",
                lead_id=None,
                kind="proposal",
                customer={"name": "X"},
                line_items=[{"description": "A", "qty": 1, "unit_price": 1000}],
            )

        assert result["id"] == "doc_pdf"

    def test_reply_missing_content_base64_raises(self):
        tenant = {"id": "t1", "business_name": "Shop", "plan": "professional"}
        db = _fake_supabase(tenant)

        reply = '{"file_name": "x.docx", "file_type": "docx", "total": 100, "summary": "ok"}'
        mock_client, mock_handle = _mock_agent_session(reply)

        with (
            patch("backend.services.document_drafting.get_service_supabase", return_value=db),
            patch("backend.services.document_drafting.ManagedAgentsClient", return_value=mock_client),
            patch("backend.services.document_drafting.document_drafter", return_value=mock_handle),
        ):
            with pytest.raises(DocumentDraftingError, match="missing content_base64"):
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

        reply = (
            '{"file_name": "x.zip", "file_type": "zip", "total": 1, '
            '"summary": "ok", "content_base64": "aGVsbG8="}'
        )
        mock_client, mock_handle = _mock_agent_session(reply)

        with (
            patch("backend.services.document_drafting.get_service_supabase", return_value=db),
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

    def test_bad_magic_bytes_rejected(self):
        """If the agent returns base64 that decodes to something that
        isn't actually a DOCX, we must reject it rather than persist
        garbage."""
        tenant = {"id": "t1", "business_name": "Shop", "plan": "growth"}
        db = _fake_supabase(tenant)

        fake_not_docx = base64.b64encode(b"this is not a docx").decode()
        reply = (
            '{"file_name": "x.docx", "file_type": "docx", "total": 1, '
            f'"summary": "ok", "content_base64": "{fake_not_docx}"}}'
        )
        mock_client, mock_handle = _mock_agent_session(reply)

        with (
            patch("backend.services.document_drafting.get_service_supabase", return_value=db),
            patch("backend.services.document_drafting.ManagedAgentsClient", return_value=mock_client),
            patch("backend.services.document_drafting.document_drafter", return_value=mock_handle),
        ):
            with pytest.raises(DocumentDraftingError, match="do not look like a docx"):
                draft_document(
                    tenant_id="t1",
                    lead_id=None,
                    kind="quote",
                    customer={"name": "X"},
                    line_items=[{"description": "A", "qty": 1, "unit_price": 1}],
                )

    def test_tool_result_base64_preferred_over_corrupted_reply(self):
        """Regression (2026-04-09): Opus corrupted the base64 it copied
        into its final reply (observed: single-char flip at offset 2762 +
        ~1900 hallucinated chars in a 14876-char docx payload). The
        ``agent.tool_result`` event that streamed the raw ``base64 -w0``
        output IS correct, so the drafter must prefer the tool_result
        over the agent's echoed copy.
        """
        tenant = {"id": "t1", "business_name": "Shop", "plan": "growth"}
        inserted = {"id": "doc_tool"}
        db = _fake_supabase(tenant, insert_result=inserted)

        # Authoritative base64 — from the tool_result stream.
        good_b64 = _FAKE_DOCX_B64

        # "Corrupted" reply — the agent flipped a middle char and appended
        # junk that makes the length mod-4 invalid.
        bad_b64 = good_b64[:10] + "X" + good_b64[11:] + "extraJunk!"

        reply = (
            '{"file_name": "quote.docx", "file_type": "docx", '
            '"total": 10, "summary": "ok", '
            f'"content_base64": "{bad_b64}"}}'
        )
        mock_client, mock_handle = _mock_agent_session(
            reply, tool_result_text=good_b64
        )

        with (
            patch("backend.services.document_drafting.get_service_supabase", return_value=db),
            patch("backend.services.document_drafting.ManagedAgentsClient", return_value=mock_client),
            patch("backend.services.document_drafting.document_drafter", return_value=mock_handle),
        ):
            result = draft_document(
                tenant_id="t1",
                lead_id=None,
                kind="quote",
                customer={"name": "X"},
                line_items=[{"description": "A", "qty": 1, "unit_price": 10}],
            )

        # The call succeeds despite the corrupted agent reply because we
        # used the tool_result base64 instead.
        assert result["id"] == "doc_tool"
        insert_call = db.table("documents").insert.call_args
        row = insert_call.args[0]
        # The decoded bytes must match the GOOD docx, not the corrupted reply.
        assert row["file_bytes"] == "\\x" + _FAKE_DOCX_BYTES.hex()

    def test_tool_result_fallback_when_reply_only(self):
        """When no ``agent.tool_result`` is captured (e.g. the agent
        used a different tool name or the stream was filtered), we must
        fall back to the agent's echoed ``content_base64``.
        """
        tenant = {"id": "t1", "business_name": "Shop", "plan": "growth"}
        inserted = {"id": "doc_fallback"}
        db = _fake_supabase(tenant, insert_result=inserted)

        reply = (
            '{"file_name": "quote.docx", "file_type": "docx", '
            '"total": 10, "summary": "ok", '
            f'"content_base64": "{_FAKE_DOCX_B64}"}}'
        )
        # No tool_result_text → only the reply is available.
        mock_client, mock_handle = _mock_agent_session(reply)

        with (
            patch("backend.services.document_drafting.get_service_supabase", return_value=db),
            patch("backend.services.document_drafting.ManagedAgentsClient", return_value=mock_client),
            patch("backend.services.document_drafting.document_drafter", return_value=mock_handle),
        ):
            result = draft_document(
                tenant_id="t1",
                lead_id=None,
                kind="quote",
                customer={"name": "X"},
                line_items=[{"description": "A", "qty": 1, "unit_price": 10}],
            )

        assert result["id"] == "doc_fallback"

    def test_whitespace_tolerant_base64(self):
        """The agent sometimes wraps base64 despite `-w0`. We should
        strip whitespace before decoding.

        Realistic failure mode: the agent omits `-w0` → `base64` emits
        wrapped output → when the agent serializes that into the JSON
        reply, the whitespace ends up as escaped `\\n` in the JSON
        source, which parses back to real `\\n` in the Python string.
        We emulate that by building the reply via json.dumps so the
        escaping matches the real wire format.
        """
        import json as _json
        tenant = {"id": "t1", "business_name": "Shop", "plan": "growth"}
        inserted = {"id": "doc_ws"}
        db = _fake_supabase(tenant, insert_result=inserted)

        # Insert real whitespace into the base64 to mimic a wrapping agent.
        wrapped = "\n".join(_FAKE_DOCX_B64[i:i + 20] for i in range(0, len(_FAKE_DOCX_B64), 20))
        reply = _json.dumps(
            {
                "file_name": "x.docx",
                "file_type": "docx",
                "total": 1,
                "summary": "ok",
                "content_base64": wrapped,
            }
        )
        mock_client, mock_handle = _mock_agent_session(reply)

        with (
            patch("backend.services.document_drafting.get_service_supabase", return_value=db),
            patch("backend.services.document_drafting.ManagedAgentsClient", return_value=mock_client),
            patch("backend.services.document_drafting.document_drafter", return_value=mock_handle),
        ):
            result = draft_document(
                tenant_id="t1",
                lead_id=None,
                kind="quote",
                customer={"name": "X"},
                line_items=[{"description": "A", "qty": 1, "unit_price": 1}],
            )

        assert result["id"] == "doc_ws"
