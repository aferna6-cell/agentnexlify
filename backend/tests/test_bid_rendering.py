"""Tests for backend/services/bid_rendering.py — pure logic, no DB / no LLM."""

import json

import pytest

from backend.services.bid_rendering import (
    build_ai_bid_prompt,
    build_business_context,
    compute_totals,
    parse_ai_bid_response,
    render_bid_html,
)


# ---------------------------------------------------------------------------
# compute_totals
# ---------------------------------------------------------------------------

class TestComputeTotals:
    def test_empty_items(self):
        subtotal, tax, total = compute_totals([])
        assert subtotal == 0.0
        assert tax == 0.0
        assert total == 0.0

    def test_single_item_with_total(self):
        items = [{"quantity": 2, "unit_price": 10.0, "total": 20.0}]
        subtotal, tax, total = compute_totals(items)
        assert subtotal == 20.0
        assert tax == 0.0
        assert total == 20.0

    def test_backfills_missing_total(self):
        items = [{"quantity": 3, "unit_price": 5.5}]
        subtotal, tax, total = compute_totals(items)
        assert items[0]["total"] == 16.5
        assert subtotal == 16.5
        assert total == 16.5

    def test_backfills_zero_total(self):
        items = [{"quantity": 4, "unit_price": 2.0, "total": 0.0}]
        subtotal, _tax, _total = compute_totals(items)
        assert items[0]["total"] == 8.0
        assert subtotal == 8.0

    def test_multiple_items_summed(self):
        items = [
            {"quantity": 2, "unit_price": 10.0, "total": 20.0},
            {"quantity": 1, "unit_price": 5.0, "total": 5.0},
            {"quantity": 3, "unit_price": 3.33},
        ]
        subtotal, _tax, total = compute_totals(items)
        assert subtotal == 34.99
        assert total == 34.99

    def test_rounds_to_two_decimals(self):
        items = [{"quantity": 3, "unit_price": 1.111}]
        subtotal, _tax, _total = compute_totals(items)
        assert subtotal == 3.33

    def test_defaults_quantity_to_1(self):
        items = [{"unit_price": 7.0}]
        subtotal, _tax, _total = compute_totals(items)
        assert subtotal == 7.0

    def test_defaults_unit_price_to_0(self):
        items = [{"quantity": 5}]
        subtotal, _tax, _total = compute_totals(items)
        assert subtotal == 0.0


# ---------------------------------------------------------------------------
# build_business_context
# ---------------------------------------------------------------------------

class TestBuildBusinessContext:
    def test_empty_when_no_name(self):
        assert build_business_context("", "painting", "Clemson") == ""

    def test_name_only(self):
        assert build_business_context("Acme", "", "") == "Business: Acme"

    def test_name_and_type(self):
        result = build_business_context("Acme", "painting", "")
        assert result == "Business: Acme (painting)"

    def test_name_and_city(self):
        result = build_business_context("Acme", "", "Clemson")
        assert result == "Business: Acme in Clemson"

    def test_full(self):
        result = build_business_context("Acme", "painting", "Clemson")
        assert result == "Business: Acme (painting) in Clemson"


# ---------------------------------------------------------------------------
# build_ai_bid_prompt
# ---------------------------------------------------------------------------

class TestBuildAIBidPrompt:
    def test_includes_job_description(self):
        prompt = build_ai_bid_prompt("Paint house exterior", "")
        assert "Paint house exterior" in prompt

    def test_includes_business_context(self):
        prompt = build_ai_bid_prompt("job", "Business: Acme in Clemson")
        assert "Business: Acme in Clemson" in prompt

    def test_demands_json_only(self):
        prompt = build_ai_bid_prompt("job", "")
        assert "Return ONLY valid JSON" in prompt
        assert "no markdown fences" in prompt

    def test_specifies_required_keys(self):
        prompt = build_ai_bid_prompt("job", "")
        for key in ("title", "description", "items", "terms", "timeline", "warranty"):
            assert key in prompt

    def test_requires_minimum_items(self):
        prompt = build_ai_bid_prompt("job", "")
        assert "at least 3 line items" in prompt


# ---------------------------------------------------------------------------
# parse_ai_bid_response
# ---------------------------------------------------------------------------

class TestParseAIBidResponse:
    def test_plain_json(self):
        raw = json.dumps({
            "title": "Exterior Paint",
            "description": "Two coats",
            "items": [
                {"description": "Labor", "quantity": 20, "unit": "hr", "unit_price": 50, "total": 1000},
            ],
            "terms": "50/50",
            "timeline": "5 days",
            "warranty": "2 years",
        })
        result = parse_ai_bid_response(raw)
        assert result["title"] == "Exterior Paint"
        assert result["description"] == "Two coats"
        assert result["subtotal"] == 1000.0
        assert result["total"] == 1000.0
        assert result["tax"] == 0.0
        assert result["terms"] == "50/50"
        assert result["timeline"] == "5 days"
        assert result["warranty"] == "2 years"

    def test_strips_markdown_fences(self):
        raw = "```json\n" + json.dumps({"title": "T", "items": []}) + "\n```"
        result = parse_ai_bid_response(raw)
        assert result["title"] == "T"
        assert result["items_json"] == []

    def test_strips_bare_triple_backticks(self):
        raw = "```\n" + json.dumps({"title": "T", "items": []}) + "\n```"
        result = parse_ai_bid_response(raw)
        assert result["title"] == "T"

    def test_backfills_missing_item_total(self):
        raw = json.dumps({
            "title": "T",
            "items": [{"description": "X", "quantity": 4, "unit_price": 2.5}],
        })
        result = parse_ai_bid_response(raw)
        assert result["items_json"][0]["total"] == 10.0
        assert result["subtotal"] == 10.0

    def test_recomputes_subtotal(self):
        raw = json.dumps({
            "title": "T",
            "items": [
                {"description": "A", "quantity": 1, "unit_price": 10, "total": 10},
                {"description": "B", "quantity": 1, "unit_price": 20, "total": 20},
            ],
        })
        result = parse_ai_bid_response(raw)
        assert result["subtotal"] == 30.0
        assert result["total"] == 30.0

    def test_missing_title_defaults(self):
        raw = json.dumps({"items": []})
        result = parse_ai_bid_response(raw)
        assert result["title"] == "Untitled Bid"

    def test_missing_optional_fields_become_none(self):
        raw = json.dumps({"title": "T", "items": []})
        result = parse_ai_bid_response(raw)
        assert result["description"] is None
        assert result["terms"] is None
        assert result["timeline"] is None
        assert result["warranty"] is None

    def test_missing_items_key_becomes_empty(self):
        raw = json.dumps({"title": "T"})
        result = parse_ai_bid_response(raw)
        assert result["items_json"] == []
        assert result["subtotal"] == 0.0

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_ai_bid_response("not json at all")


# ---------------------------------------------------------------------------
# render_bid_html — structure + XSS
# ---------------------------------------------------------------------------

class TestRenderBidHTML:
    @staticmethod
    def _bid(**overrides):
        base = {
            "title": "Bid Title",
            "description": "Bid desc",
            "items_json": [
                {"description": "Labor", "quantity": 1, "unit": "hr", "unit_price": 50, "total": 50},
            ],
            "subtotal": 50,
            "tax": 0,
            "total": 50,
            "status": "draft",
            "created_at": "2026-05-23T10:00:00Z",
            "terms": "50/50",
            "timeline": "5 days",
            "warranty": "2 years",
        }
        base.update(overrides)
        return base

    @staticmethod
    def _business(**overrides):
        base = {
            "business_name": "Acme Co",
            "owner_email": "owner@acme.test",
            "phone": "555-1234",
            "city": "Clemson",
        }
        base.update(overrides)
        return base

    @staticmethod
    def _customer(**overrides):
        base = {"name": "Jane", "email": "jane@test.com", "phone": "555-9999"}
        base.update(overrides)
        return base

    def test_includes_doctype(self):
        html_out = render_bid_html(self._bid(), self._business(), self._customer())
        assert html_out.startswith("<!DOCTYPE html>")

    def test_includes_business_name(self):
        html_out = render_bid_html(self._bid(), self._business(), self._customer())
        assert "Acme Co" in html_out

    def test_includes_title(self):
        html_out = render_bid_html(self._bid(), self._business(), self._customer())
        assert "Bid Title" in html_out

    def test_includes_totals_formatted(self):
        bid = self._bid(subtotal=1234.5, total=1234.5)
        html_out = render_bid_html(bid, self._business(), self._customer())
        assert "$1,234.50" in html_out

    def test_includes_customer_block(self):
        html_out = render_bid_html(self._bid(), self._business(), self._customer())
        assert "Jane" in html_out
        assert "jane@test.com" in html_out
        assert "555-9999" in html_out

    def test_omits_customer_block_when_all_empty(self):
        html_out = render_bid_html(
            self._bid(), self._business(), {"name": "", "email": "", "phone": ""}
        )
        assert "Prepared For" not in html_out

    def test_omits_optional_sections_when_empty(self):
        bid = self._bid(terms="", timeline="", warranty="")
        html_out = render_bid_html(bid, self._business(), self._customer())
        # Section header is in an <h3>; CSS/comments may mention labels, so
        # match the rendered section heading specifically.
        assert ">Payment Terms<" not in html_out
        assert ">Timeline<" not in html_out
        assert ">Warranty<" not in html_out

    def test_includes_optional_sections_when_set(self):
        html_out = render_bid_html(self._bid(), self._business(), self._customer())
        assert ">Payment Terms<" in html_out
        assert ">Timeline<" in html_out
        assert ">Warranty<" in html_out

    # --- XSS hardening ----------------------------------------------------

    def test_escapes_title(self):
        bid = self._bid(title="<script>alert(1)</script>")
        html_out = render_bid_html(bid, self._business(), self._customer())
        assert "<script>alert(1)</script>" not in html_out
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_out

    def test_escapes_description(self):
        bid = self._bid(description="<img src=x onerror=alert(1)>")
        html_out = render_bid_html(bid, self._business(), self._customer())
        assert "<img src=x onerror=alert(1)>" not in html_out
        assert "&lt;img" in html_out

    def test_escapes_terms_timeline_warranty(self):
        bid = self._bid(
            terms="<b>terms</b>",
            timeline="<b>timeline</b>",
            warranty="<b>warranty</b>",
        )
        html_out = render_bid_html(bid, self._business(), self._customer())
        assert "<b>terms</b>" not in html_out
        assert "<b>timeline</b>" not in html_out
        assert "<b>warranty</b>" not in html_out
        assert "&lt;b&gt;terms&lt;/b&gt;" in html_out

    def test_escapes_business_fields(self):
        biz = self._business(
            business_name="<script>x</script>",
            owner_email="a@b.com\"<script>",
            phone="<x>",
            city="<y>",
        )
        html_out = render_bid_html(self._bid(), biz, self._customer())
        assert "<script>x</script>" not in html_out
        assert "&lt;script&gt;x&lt;/script&gt;" in html_out

    def test_escapes_customer_fields(self):
        cust = {
            "name": "<script>n</script>",
            "email": "<script>e</script>",
            "phone": "<script>p</script>",
        }
        html_out = render_bid_html(self._bid(), self._business(), cust)
        assert "<script>n</script>" not in html_out
        assert "<script>e</script>" not in html_out
        assert "<script>p</script>" not in html_out

    def test_escapes_line_item_fields(self):
        bid = self._bid(items_json=[
            {
                "description": "<script>desc</script>",
                "quantity": "<x>",
                "unit": "<y>",
                "unit_price": 1,
                "total": 1,
            }
        ])
        html_out = render_bid_html(bid, self._business(), self._customer())
        assert "<script>desc</script>" not in html_out
        assert "&lt;script&gt;desc&lt;/script&gt;" in html_out
        assert "&lt;x&gt;" in html_out
        assert "&lt;y&gt;" in html_out

    def test_invalid_unit_price_coerces_to_zero(self):
        bid = self._bid(items_json=[
            {"description": "X", "quantity": 1, "unit": "hr", "unit_price": "bad", "total": 0}
        ])
        html_out = render_bid_html(bid, self._business(), self._customer())
        assert "$0.00" in html_out

    def test_invalid_subtotal_coerces_to_zero(self):
        bid = self._bid(subtotal="not-a-number", total="also-bad", tax=None)
        html_out = render_bid_html(bid, self._business(), self._customer())
        assert html_out.startswith("<!DOCTYPE html>")

    def test_default_status_draft(self):
        bid = self._bid(status="")
        html_out = render_bid_html(bid, self._business(), self._customer())
        assert "draft" in html_out

    def test_handles_missing_created_at(self):
        bid = self._bid(created_at="")
        html_out = render_bid_html(bid, self._business(), self._customer())
        assert html_out.startswith("<!DOCTYPE html>")

    def test_handles_malformed_created_at(self):
        bid = self._bid(created_at="not-a-date")
        html_out = render_bid_html(bid, self._business(), self._customer())
        assert html_out.startswith("<!DOCTYPE html>")

    def test_iso_date_formatted(self):
        bid = self._bid(created_at="2026-05-23T10:00:00Z")
        html_out = render_bid_html(bid, self._business(), self._customer())
        assert "May 23, 2026" in html_out

    def test_empty_items_renders_empty_table_body(self):
        bid = self._bid(items_json=[])
        html_out = render_bid_html(bid, self._business(), self._customer())
        assert "<tbody>" in html_out

    def test_default_business_name_when_missing(self):
        biz = {"business_name": "", "owner_email": "", "phone": "", "city": ""}
        html_out = render_bid_html(self._bid(), biz, self._customer())
        assert "Business" in html_out

    def test_default_title_when_missing(self):
        bid = self._bid(title="")
        html_out = render_bid_html(bid, self._business(), self._customer())
        assert "Bid" in html_out
