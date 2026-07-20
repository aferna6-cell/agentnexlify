"""Characterization tests for the invoices router (issue #473 split).

Pin the endpoint contracts of backend/routers/invoices.py BEFORE splitting
the 1,243-line god class, so the split can be verified behavior-identical.
Endpoint-level through the real ASGI app with the mock Supabase client.

External I/O is patched at the invoices-module call sites (send_email,
send_sms, _get_or_create_stripe_payment_link); when the split moves those
call sites the patch paths move with them — assertions stay unchanged.
"""

from unittest.mock import ANY, AsyncMock, MagicMock, patch

TENANT_ID = "9a000000-0000-4000-8000-000000000001"
BASE = f"/api/v1/invoices/{TENANT_ID}"


class _Chain:
    def __init__(self, result):
        self._result = result

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def _method(*args, **kwargs):
            if name == "execute":
                return self._result
            return self

        return _method


def _result(data=None, count=None):
    m = MagicMock()
    m.data = data if data is not None else []
    m.count = count if count is not None else len(m.data)
    return m


def _seed(mock_supabase, tables: dict):
    """tables maps name -> dict(select=[rows], insert=[rows], update=[rows],
    insert_side=callable) — unlisted tables return empty results."""
    built: dict[str, MagicMock] = {}

    def _tbl(cfg):
        tbl = MagicMock()
        calls = {"insert": [], "update": []}
        tbl._calls = calls

        select_rows = cfg.get("select", [])
        select_seq = cfg.get("select_seq")
        state = {"select_i": 0}

        def _select(*a, **k):
            if select_seq is not None:
                rows = select_seq[min(state["select_i"], len(select_seq) - 1)]
                state["select_i"] += 1
                return _Chain(_result(rows))
            return _Chain(_result(select_rows, count=cfg.get("count")))

        def _insert(*a, **k):
            calls["insert"].append(a[0] if a else k)
            side = cfg.get("insert_side")
            if side is not None:
                return side(len(calls["insert"]), a[0] if a else k)
            return _Chain(_result(cfg.get("insert", select_rows)))

        def _update(*a, **k):
            calls["update"].append(a[0] if a else k)
            return _Chain(_result(cfg.get("update", select_rows)))

        tbl.select.side_effect = _select
        tbl.insert.side_effect = _insert
        tbl.update.side_effect = _update
        tbl.delete.side_effect = lambda *a, **k: _Chain(_result(cfg.get("delete", [])))
        return tbl

    def table_side_effect(name):
        if name not in built:
            built[name] = _tbl(tables.get(name, {}))
        return built[name]

    mock_supabase.table.side_effect = table_side_effect
    return built


class TestInvoiceStats:
    def test_stats_aggregates(self, client, mock_supabase, auth_headers_for):
        rows = [
            {"status": "sent", "total": 100.0, "sent_at": None, "paid_at": None},
            {"status": "viewed", "total": 50.0, "sent_at": None, "paid_at": None},
            {
                "status": "paid",
                "total": 200.0,
                "sent_at": "2026-07-01T00:00:00Z",
                "paid_at": "2026-07-05T00:00:00Z",
            },
            {"status": "overdue", "total": 75.0, "sent_at": None, "paid_at": None},
        ]
        _seed(mock_supabase, {"invoices": {"select": rows}})
        resp = client.get(f"{BASE}/stats", headers=auth_headers_for(TENANT_ID))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_outstanding"] == 150.0
        assert body["total_paid"] == 200.0
        assert body["overdue_count"] == 1
        assert body["paid_count"] == 1
        assert body["total_invoices"] == 4
        assert body["avg_days_to_payment"] == 4.0

    def test_stats_wrong_tenant_403(self, client, mock_supabase, auth_headers_for):
        _seed(mock_supabase, {})
        resp = client.get(
            f"{BASE}/stats",
            headers=auth_headers_for("00000000-0000-4000-8000-00000000beef"),
        )
        assert resp.status_code == 403


class TestCreateInvoice:
    def test_create_computes_totals_and_number(
        self, client, mock_supabase, auth_headers_for
    ):
        created = {"id": "inv-1", "invoice_number": "9A00", "total": 108.68}
        tbls = _seed(
            mock_supabase,
            {
                "invoices": {
                    "select": [{"invoice_number": "INV-9A00-007"}],
                    "insert": [created],
                }
            },
        )
        resp = client.post(
            BASE,
            json={
                "items": [
                    {"description": "Drain cleaning", "quantity": 2, "unit_price": 49.5}
                ],
                "tax_rate": 9.78,
            },
            headers=auth_headers_for(TENANT_ID),
        )
        assert resp.status_code == 201, resp.text
        payload = tbls["invoices"]._calls["insert"][0]
        assert payload["invoice_number"] == "INV-9A00-008"
        assert payload["subtotal"] == 99.0
        assert payload["tax_amount"] == 9.68
        assert payload["total"] == 108.68
        assert payload["status"] == "draft"

    def test_create_deposit_exceeding_total_400(
        self, client, mock_supabase, auth_headers_for
    ):
        _seed(mock_supabase, {"invoices": {"select": []}})
        resp = client.post(
            BASE,
            json={
                "items": [{"description": "x", "quantity": 1, "unit_price": 10}],
                "tax_rate": 0,
                "deposit_amount": 50,
            },
            headers=auth_headers_for(TENANT_ID),
        )
        assert resp.status_code == 400
        assert "deposit_amount" in resp.text

    def test_create_retries_on_unique_conflict(
        self, client, mock_supabase, auth_headers_for
    ):
        created = {"id": "inv-2", "invoice_number": "INV-9A00-002"}

        def insert_side(call_no, payload):
            if call_no == 1:
                raise RuntimeError("duplicate key value idx_invoices_tenant_number")
            return _Chain(_result([created]))

        tbls = _seed(
            mock_supabase,
            {"invoices": {"select": [], "insert_side": insert_side}},
        )
        resp = client.post(
            BASE,
            json={"items": [{"description": "y", "quantity": 1, "unit_price": 5}]},
            headers=auth_headers_for(TENANT_ID),
        )
        assert resp.status_code == 201, resp.text
        assert len(tbls["invoices"]._calls["insert"]) == 2

    def test_create_recurring_sets_next_date(
        self, client, mock_supabase, auth_headers_for
    ):
        tbls = _seed(
            mock_supabase,
            {"invoices": {"select": [], "insert": [{"id": "inv-3"}]}},
        )
        resp = client.post(
            BASE,
            json={
                "items": [{"description": "retainer", "quantity": 1, "unit_price": 100}],
                "is_recurring": True,
                "recurrence_interval": "monthly",
                "due_date": "2026-08-01",
            },
            headers=auth_headers_for(TENANT_ID),
        )
        assert resp.status_code == 201, resp.text
        payload = tbls["invoices"]._calls["insert"][0]
        assert payload["is_recurring"] is True
        assert payload["next_invoice_date"] == "2026-09-01"


class TestCreateFromBid:
    def test_accepted_bid_becomes_invoice(
        self, client, mock_supabase, auth_headers_for
    ):
        bid = {
            "id": "bid-1",
            "status": "accepted",
            "lead_id": "lead-1",
            "title": "Water heater install",
            "items_json": [{"description": "Heater", "quantity": 1, "unit_price": 900}],
        }
        created = {"id": "inv-b1", "invoice_number": "INV-9A00-001"}
        tbls = _seed(
            mock_supabase,
            {
                "bids": {"select": [bid]},
                "invoices": {"select": [], "insert": [created]},
            },
        )
        resp = client.post(
            f"{BASE}/from-bid/bid-1", headers=auth_headers_for(TENANT_ID)
        )
        assert resp.status_code == 201, resp.text
        payload = tbls["invoices"]._calls["insert"][0]
        assert payload["bid_id"] == "bid-1"
        assert payload["lead_id"] == "lead-1"
        assert payload["total"] == 900.0
        assert "Water heater install" in payload["notes"]

    def test_non_accepted_bid_400(self, client, mock_supabase, auth_headers_for):
        _seed(mock_supabase, {"bids": {"select": [{"id": "bid-2", "status": "draft"}]}})
        resp = client.post(
            f"{BASE}/from-bid/bid-2", headers=auth_headers_for(TENANT_ID)
        )
        assert resp.status_code == 400
        assert "accepted" in resp.text

    def test_missing_bid_404(self, client, mock_supabase, auth_headers_for):
        _seed(mock_supabase, {"bids": {"select": []}})
        resp = client.post(
            f"{BASE}/from-bid/bid-3", headers=auth_headers_for(TENANT_ID)
        )
        assert resp.status_code == 404

    def test_duplicate_invoice_409(self, client, mock_supabase, auth_headers_for):
        bid = {"id": "bid-4", "status": "accepted", "items_json": []}
        _seed(
            mock_supabase,
            {
                "bids": {"select": [bid]},
                "invoices": {"select": [{"id": "inv-x", "invoice_number": "INV-9A00-004"}]},
            },
        )
        resp = client.post(
            f"{BASE}/from-bid/bid-4", headers=auth_headers_for(TENANT_ID)
        )
        assert resp.status_code == 409


class TestListAndGet:
    def test_list_enriches_lead_names(self, client, mock_supabase, auth_headers_for):
        invs = [
            {"id": "i1", "lead_id": "l1", "total": 10},
            {"id": "i2", "lead_id": None, "total": 20},
        ]
        _seed(
            mock_supabase,
            {
                "invoices": {"select": invs, "count": 2},
                "leads": {"select": [{"id": "l1", "name": "Pat Doe"}]},
            },
        )
        resp = client.get(BASE, headers=auth_headers_for(TENANT_ID))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["count"] == 2
        assert body["invoices"][0]["lead_name"] == "Pat Doe"
        assert body["invoices"][1]["lead_name"] == ""

    def test_get_enriches_lead(self, client, mock_supabase, auth_headers_for):
        _seed(
            mock_supabase,
            {
                "invoices": {"select": [{"id": "i9", "lead_id": "l9"}]},
                "leads": {
                    "select": [
                        {"id": "l9", "name": "Sam", "email": "s@x.co", "phone": "+15550000000"}
                    ]
                },
            },
        )
        resp = client.get(f"{BASE}/i9", headers=auth_headers_for(TENANT_ID))
        assert resp.status_code == 200, resp.text
        assert resp.json()["lead"]["name"] == "Sam"

    def test_get_404(self, client, mock_supabase, auth_headers_for):
        _seed(mock_supabase, {"invoices": {"select": []}})
        resp = client.get(f"{BASE}/i404", headers=auth_headers_for(TENANT_ID))
        assert resp.status_code == 404


class TestItemTemplates:
    def test_template_crud_contract(self, client, mock_supabase, auth_headers_for):
        tpl = {"id": "t1", "description": "Service call", "unit_price": 89.0}
        _seed(
            mock_supabase,
            {"invoice_item_templates": {"select": [tpl], "insert": [tpl], "update": [tpl]}},
        )
        headers = auth_headers_for(TENANT_ID)

        assert client.get(f"{BASE}/item-templates", headers=headers).json() == [tpl]
        assert (
            client.post(
                f"{BASE}/item-templates",
                json={"description": "Service call", "unit_price": 89.0},
                headers=headers,
            ).status_code
            == 200
        )
        assert (
            client.put(
                f"{BASE}/item-templates/t1",
                json={"unit_price": 99.0},
                headers=headers,
            ).status_code
            == 200
        )
        assert client.delete(f"{BASE}/item-templates/t1", headers=headers).json() == {
            "deleted": True
        }

    def test_template_update_no_fields_400(
        self, client, mock_supabase, auth_headers_for
    ):
        _seed(mock_supabase, {"invoice_item_templates": {"select": []}})
        resp = client.put(
            f"{BASE}/item-templates/t2", json={}, headers=auth_headers_for(TENANT_ID)
        )
        assert resp.status_code == 400

    def test_template_update_404(self, client, mock_supabase, auth_headers_for):
        _seed(mock_supabase, {"invoice_item_templates": {"select": [], "update": []}})
        resp = client.put(
            f"{BASE}/item-templates/t3",
            json={"unit_price": 1.0},
            headers=auth_headers_for(TENANT_ID),
        )
        assert resp.status_code == 404


class TestUpdateAndDelete:
    def test_update_draft_recalculates_totals(
        self, client, mock_supabase, auth_headers_for
    ):
        existing = {"status": "draft", "tax_rate": 10.0, "items_json": []}
        updated = {"id": "i1", "total": 55.0}
        tbls = _seed(
            mock_supabase,
            {"invoices": {"select": [existing], "update": [updated]}},
        )
        resp = client.put(
            f"{BASE}/i1",
            json={"items": [{"description": "z", "quantity": 1, "unit_price": 50}]},
            headers=auth_headers_for(TENANT_ID),
        )
        assert resp.status_code == 200, resp.text
        payload = tbls["invoices"]._calls["update"][0]
        assert payload["subtotal"] == 50.0
        assert payload["tax_amount"] == 5.0
        assert payload["total"] == 55.0

    def test_update_non_draft_400(self, client, mock_supabase, auth_headers_for):
        _seed(mock_supabase, {"invoices": {"select": [{"status": "sent"}]}})
        resp = client.put(
            f"{BASE}/i2",
            json={"notes": "late fee applies"},
            headers=auth_headers_for(TENANT_ID),
        )
        assert resp.status_code == 400
        assert "draft" in resp.text

    def test_update_no_fields_400(self, client, mock_supabase, auth_headers_for):
        _seed(
            mock_supabase,
            {"invoices": {"select": [{"status": "draft", "tax_rate": 0, "items_json": []}]}},
        )
        resp = client.put(
            f"{BASE}/i3", json={}, headers=auth_headers_for(TENANT_ID)
        )
        assert resp.status_code == 400

    def test_delete_draft_only(self, client, mock_supabase, auth_headers_for):
        _seed(mock_supabase, {"invoices": {"select": [{"status": "draft"}]}})
        resp = client.request(
            "DELETE", f"{BASE}/i4", headers=auth_headers_for(TENANT_ID)
        )
        assert resp.status_code == 200
        assert resp.json() == {"deleted": True}

    def test_delete_sent_400(self, client, mock_supabase, auth_headers_for):
        _seed(mock_supabase, {"invoices": {"select": [{"status": "sent"}]}})
        resp = client.request(
            "DELETE", f"{BASE}/i5", headers=auth_headers_for(TENANT_ID)
        )
        assert resp.status_code == 400


class TestSendInvoice:
    def _invoice(self, **over):
        row = {
            "id": "i7",
            "status": "draft",
            "invoice_number": "INV-9A00-007",
            "total": 120.0,
            "lead_id": "l7",
            "items_json": [],
            "subtotal": 120.0,
            "tax_amount": 0,
            "stripe_payment_link": None,
            "notes": None,
            "due_date": None,
        }
        row.update(over)
        return row

    def test_send_email_success(self, client, mock_supabase, auth_headers_for):
        tbls = _seed(
            mock_supabase,
            {
                "invoices": {"select": [self._invoice()]},
                "tenants": {
                    "select": [
                        {"business_name": "Pipe Co", "owner_email": "o@p.co", "phone": None}
                    ]
                },
                "leads": {
                    "select": [
                        {"id": "l7", "name": "Ana", "email": "ana@x.co", "phone": None}
                    ]
                },
            },
        )
        email = AsyncMock(return_value={"success": True})
        with patch("backend.services.invoice_send.send_email", new=email), patch(
            "backend.services.invoice_send.get_or_create_stripe_payment_link",
            new=AsyncMock(return_value="https://pay.example/x"),
        ):
            resp = client.post(
                f"{BASE}/i7/send",
                json={"method": "email"},
                headers=auth_headers_for(TENANT_ID),
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["sent"] is True
        assert body["email_sent"] is True
        assert body["payment_link"] == "https://pay.example/x"
        assert body["errors"] == []
        email.assert_awaited_once()
        update_payload = tbls["invoices"]._calls["update"][0]
        assert update_payload["status"] == "sent"
        assert update_payload["sent_via"] == "email"

    def test_send_paid_invoice_400(self, client, mock_supabase, auth_headers_for):
        _seed(mock_supabase, {"invoices": {"select": [self._invoice(status="paid")]}})
        resp = client.post(
            f"{BASE}/i7/send",
            json={"method": "email"},
            headers=auth_headers_for(TENANT_ID),
        )
        assert resp.status_code == 400

    def test_send_missing_email_collects_error(
        self, client, mock_supabase, auth_headers_for
    ):
        _seed(
            mock_supabase,
            {
                "invoices": {"select": [self._invoice()]},
                "tenants": {"select": [{"business_name": "Pipe Co"}]},
                "leads": {"select": [{"id": "l7", "name": "Ana", "email": None, "phone": None}]},
            },
        )
        with patch(
            "backend.services.invoice_send.get_or_create_stripe_payment_link",
            new=AsyncMock(return_value=None),
        ):
            resp = client.post(
                f"{BASE}/i7/send",
                json={"method": "email"},
                headers=auth_headers_for(TENANT_ID),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["email_sent"] is False
        assert any("email" in e.lower() for e in body["errors"])


class TestPayments:
    def test_mark_paid(self, client, mock_supabase, auth_headers_for):
        paid_row = {"id": "i8", "invoice_number": "INV-9A00-008", "total": 10, "lead_id": None}
        _seed(
            mock_supabase,
            {"invoices": {"select": [{"status": "sent"}], "update": [paid_row]}},
        )
        resp = client.post(
            f"{BASE}/i8/mark-paid",
            json={"payment_method": "cash"},
            headers=auth_headers_for(TENANT_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == "i8"

    def test_mark_paid_twice_400(self, client, mock_supabase, auth_headers_for):
        _seed(mock_supabase, {"invoices": {"select": [{"status": "paid"}]}})
        resp = client.post(
            f"{BASE}/i8/mark-paid", json={}, headers=auth_headers_for(TENANT_ID)
        )
        assert resp.status_code == 400
        assert "already" in resp.text

    def test_record_partial_payment(self, client, mock_supabase, auth_headers_for):
        tbls = _seed(
            mock_supabase,
            {
                "invoices": {
                    "select": [{"total": 100.0, "amount_paid": 40.0, "status": "sent"}],
                    "update": [{"id": "i9", "amount_paid": 70.0}],
                }
            },
        )
        resp = client.post(
            f"{BASE}/i9/record-payment",
            json={"amount": 30},
            headers=auth_headers_for(TENANT_ID),
        )
        assert resp.status_code == 200, resp.text
        payload = tbls["invoices"]._calls["update"][0]
        assert payload["amount_paid"] == 70.0
        assert "status" not in payload

    def test_record_payment_overpay_400(self, client, mock_supabase, auth_headers_for):
        _seed(
            mock_supabase,
            {"invoices": {"select": [{"total": 100.0, "amount_paid": 90.0, "status": "sent"}]}},
        )
        resp = client.post(
            f"{BASE}/i9/record-payment",
            json={"amount": 50},
            headers=auth_headers_for(TENANT_ID),
        )
        assert resp.status_code == 400
        assert "exceeds" in resp.text

    def test_record_payment_completes_invoice(
        self, client, mock_supabase, auth_headers_for
    ):
        tbls = _seed(
            mock_supabase,
            {
                "invoices": {
                    "select": [{"total": 100.0, "amount_paid": 60.0, "status": "sent"}],
                    "update": [{"id": "i10", "status": "paid"}],
                }
            },
        )
        resp = client.post(
            f"{BASE}/i10/record-payment",
            json={"amount": 40, "payment_method": "card"},
            headers=auth_headers_for(TENANT_ID),
        )
        assert resp.status_code == 200
        payload = tbls["invoices"]._calls["update"][0]
        assert payload["status"] == "paid"
        assert payload["payment_method"] == "card"


class TestBulkSend:
    def test_bulk_send_mixed_results(self, client, mock_supabase, auth_headers_for):
        invoices = [
            {
                "id": "b1",
                "status": "draft",
                "invoice_number": "INV-9A00-020",
                "total": 40.0,
                "lead_id": "l1",
                "stripe_payment_link": "https://pay.example/b1",
            },
            {
                "id": "b2",
                "status": "paid",
                "invoice_number": "INV-9A00-021",
                "total": 60.0,
                "lead_id": "l1",
            },
        ]
        tbls = _seed(
            mock_supabase,
            {
                "invoices": {"select": invoices},
                "tenants": {"select": [{"business_name": "Pipe Co"}]},
                "leads": {
                    "select": [
                        {"id": "l1", "name": "Ana", "email": "ana@x.co", "phone": None}
                    ]
                },
            },
        )
        email = AsyncMock(return_value={"success": True})
        with patch("backend.services.invoice_send.send_email", new=email):
            resp = client.post(
                f"{BASE}/bulk-send",
                json={"invoice_ids": ["b1", "b2"], "channel": "email"},
                headers=auth_headers_for(TENANT_ID),
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["sent"] == 1
        assert body["failed"] == 1
        assert any("already paid" in e for e in body["errors"])
        email.assert_awaited_once()
        update_payload = tbls["invoices"]._calls["update"][0]
        assert update_payload["status"] == "sent"

    def test_bulk_send_missing_invoice_counts_failed(
        self, client, mock_supabase, auth_headers_for
    ):
        _seed(
            mock_supabase,
            {"invoices": {"select": []}, "tenants": {"select": []}},
        )
        resp = client.post(
            f"{BASE}/bulk-send",
            json={"invoice_ids": ["ghost"], "channel": "email"},
            headers=auth_headers_for(TENANT_ID),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["sent"] == 0
        assert body["failed"] == 1
