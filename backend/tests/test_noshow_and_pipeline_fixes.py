"""Regression tests for bugs fixed in 2026-04-09 hard debug session.

Covers:
- bug-patterns #70: noshow follow-up silently dropped when tenant not in cache
- bug-patterns #71: pipeline notify_team email XSS via unescaped HTML
- bug-patterns #72: noshow_recovery unsubscribe check failure must default-deny (CAN-SPAM)
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Bug #70 — noshow_recovery._send_noshow_followups lazy-loads tenant
# ---------------------------------------------------------------------------


class TestNoshowFollowupTenantCache:
    """Regression: _send_noshow_followups must lazy-load tenants that
    weren't populated into the shared cache by the primary loop.
    """

    def _make_followup_appt(self, tenant_id="tenant-abc"):
        return {
            "id": "appt-999",
            "tenant_id": tenant_id,
            "customer_name": "Jane Doe",
            "customer_email": "jane@example.com",
            "customer_phone": "+15555551234",
            "lead_id": "lead-555",
            "noshow_recovery_sent_at": "2026-04-08T00:00:00+00:00",
        }

    def _make_tenant_row(self):
        return {
            "business_name": "Acme Co",
            "plan": "growth",
            "google_review_link": None,
            "owner_email": "owner@acme.test",
            "noshow_recovery_enabled": True,
        }

    def test_followup_loads_tenant_when_not_in_cache(self):
        """When tenant_cache is empty but a stale follow-up exists, the
        function must fetch the tenant instead of silently skipping it.
        """
        from backend.services import noshow_recovery

        tenant_id = "tenant-abc"
        appt = self._make_followup_appt(tenant_id)
        tenant_row = self._make_tenant_row()

        followup_query = MagicMock()
        followup_query.data = [appt]

        tenant_query = MagicMock()
        tenant_query.data = [tenant_row]

        # Track which table was queried so we can verify tenant lookup happened
        table_calls: list[str] = []

        def table_side_effect(table_name):
            table_calls.append(table_name)
            chain = MagicMock()
            if table_name == "appointments":
                # First call = the follow-up query; any later calls = update/check
                chain.select.return_value.eq.return_value.filter.return_value.is_.return_value.lte.return_value.limit.return_value.execute.return_value = (
                    followup_query
                )
                # rebooked check + mark followup
                chain.update.return_value.eq.return_value.execute.return_value = (
                    MagicMock(data=[])
                )
            elif table_name == "tenants":
                chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                    tenant_query
                )
            else:
                chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[]
                )
            return chain

        db = MagicMock()
        db.table.side_effect = table_side_effect

        # Stub SMS/email so we don't actually send
        with (
            patch.object(noshow_recovery, "send_sms", new=AsyncMock(return_value=True)),
            patch.object(
                noshow_recovery,
                "send_email",
                new=AsyncMock(return_value={"success": True}),
            ),
            patch.object(noshow_recovery, "check_sms_rate_limit", return_value=True),
            patch.object(noshow_recovery, "increment_sms_count"),
            patch.object(
                noshow_recovery,
                "build_unsubscribe_url",
                return_value="https://unsub.test",
            ),
        ):
            cache: dict[str, dict | None] = {}  # starts EMPTY — the bug case
            now = datetime.now(timezone.utc)

            sent = asyncio.run(noshow_recovery._send_noshow_followups(db, now, cache))

            # The tenant must have been fetched and cached
            assert tenant_id in cache, (
                "regression: tenant was never loaded into cache — "
                "followup silently skipped (bug-patterns #70)"
            )
            assert cache[tenant_id] is not None
            assert cache[tenant_id]["business_name"] == "Acme Co"
            # And the tenant table must have been queried
            assert "tenants" in table_calls, "tenant table was never queried"
            # Some outbound message should have been recorded
            assert sent >= 0  # sanity — function returned without error

    def test_followup_skips_when_feature_toggle_off(self):
        """Tenant with noshow_recovery_enabled=False must be skipped in the
        follow-up path. Pre-populates the cache so the assertion isolates
        the toggle check from the separate lazy-load fix (bug-patterns #70).
        Clears customer_email so the rebook check is bypassed — otherwise
        MagicMock's truthy auto-attributes make the old code short-circuit
        via `if rebooked.data:` before ever reaching the send path.
        """
        from backend.services import noshow_recovery

        tenant_id = "tenant-xyz"
        appt = self._make_followup_appt(tenant_id)
        appt["customer_email"] = None  # bypass rebook check
        tenant_row = self._make_tenant_row()
        tenant_row["noshow_recovery_enabled"] = False

        followup_query = MagicMock()
        followup_query.data = [appt]

        def table_side_effect(table_name):
            chain = MagicMock()
            if table_name == "appointments":
                chain.select.return_value.eq.return_value.filter.return_value.is_.return_value.lte.return_value.limit.return_value.execute.return_value = (
                    followup_query
                )
                chain.update.return_value.eq.return_value.execute.return_value = (
                    MagicMock(data=[])
                )
            else:
                chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[]
                )
            return chain

        db = MagicMock()
        db.table.side_effect = table_side_effect

        send_sms_mock = AsyncMock(return_value=True)
        send_email_mock = AsyncMock(return_value={"success": True})

        with (
            patch.object(noshow_recovery, "send_sms", new=send_sms_mock),
            patch.object(noshow_recovery, "send_email", new=send_email_mock),
            patch.object(noshow_recovery, "check_sms_rate_limit", return_value=True),
            patch.object(noshow_recovery, "increment_sms_count"),
            patch.object(
                noshow_recovery,
                "build_unsubscribe_url",
                return_value="https://unsub.test",
            ),
        ):
            # IMPORTANT: pre-populate cache so we're NOT testing the lazy-load
            # path. This isolates the toggle-off defense-in-depth check.
            cache: dict[str, dict | None] = {tenant_id: tenant_row}
            sent = asyncio.run(
                noshow_recovery._send_noshow_followups(
                    db,
                    datetime.now(timezone.utc),
                    cache,
                )
            )

            assert sent == 0
            send_sms_mock.assert_not_called()
            send_email_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Bug #72 — noshow_recovery unsubscribe check must default-deny on failure
# ---------------------------------------------------------------------------


class TestNoshowRecoveryUnsubscribeDefaultDeny:
    """Regression: when the unsubscribe-status lookup on `leads` raises,
    we must NOT proceed to send SMS/email. CAN-SPAM requires default-deny.
    Previously the exception was swallowed at debug-level and the loop
    proceeded to contact a potentially-unsubscribed customer.
    """

    def test_unsubscribe_check_exception_skips_send(self):
        from backend.services import noshow_recovery

        tenant_id = "tenant-csp"
        appt = {
            "id": "appt-unsub",
            "tenant_id": tenant_id,
            "customer_name": "Pat Doe",
            "customer_email": "pat@example.com",
            "customer_phone": "+15555557777",
            "start_time": "2026-04-23T10:00:00+00:00",
            "updated_at": "2026-04-22T10:00:00+00:00",
            "lead_id": "lead-unsub",
        }
        tenant_row = {
            "business_name": "Acme Co",
            "plan": "growth",
            "google_review_link": None,
            "owner_email": "owner@acme.test",
            "noshow_recovery_enabled": True,
        }

        appt_query = MagicMock()
        appt_query.data = [appt]
        tenant_query = MagicMock()
        tenant_query.data = [tenant_row]

        def table_side_effect(name):
            chain = MagicMock()
            if name == "appointments":
                chain.select.return_value.eq.return_value.is_.return_value.limit.return_value.execute.return_value = (
                    appt_query
                )
                chain.select.return_value.eq.return_value.not_.is_.return_value.is_.return_value.lte.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[]
                )
                chain.update.return_value.eq.return_value.execute.return_value = (
                    MagicMock(data=[])
                )
            elif name == "tenants":
                chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                    tenant_query
                )
            elif name == "leads":
                # Raise on unsubscribe lookup — forces default-deny path
                chain.select.return_value.eq.return_value.limit.return_value.execute.side_effect = RuntimeError(
                    "supabase down"
                )
            elif name == "activity_log":
                chain.insert.return_value.execute.return_value = MagicMock(data=[])
            else:
                chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[]
                )
            return chain

        db = MagicMock()
        db.table.side_effect = table_side_effect

        send_sms_mock = AsyncMock(return_value=True)
        send_email_mock = AsyncMock(return_value={"success": True})

        with (
            patch.object(noshow_recovery, "get_service_supabase", return_value=db),
            patch.object(noshow_recovery, "send_sms", new=send_sms_mock),
            patch.object(noshow_recovery, "send_email", new=send_email_mock),
            patch.object(noshow_recovery, "check_sms_rate_limit", return_value=True),
            patch.object(noshow_recovery, "increment_sms_count"),
            patch.object(
                noshow_recovery,
                "build_unsubscribe_url",
                return_value="https://unsub.test",
            ),
            patch.object(noshow_recovery, "fire_event_background"),
        ):
            sent = asyncio.run(noshow_recovery.process_noshow_recovery())

            assert sent == 0, (
                "regression: unsubscribe check failure must default-deny — "
                "no messages should be sent (bug-patterns #72)"
            )
            send_sms_mock.assert_not_called()
            send_email_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Bug #71 — pipeline_automations notify_team escapes HTML
# ---------------------------------------------------------------------------


class TestPipelineNotifyTeamEscaping:
    """Regression: _execute_notify_team_action must HTML-escape every
    user-controlled value (lead name, stage names, message) before
    interpolating into the email body.
    """

    def test_notify_team_escapes_injected_html_in_lead_name(self):
        from backend.routers import pipeline_automations

        malicious_name = "<img src=x onerror=alert(1)>"
        lead = {"id": "lead-1", "name": malicious_name, "email": "l@example.com"}
        tenant = {
            "id": "tenant-1",
            "business_name": "Acme <Corp>",
            "owner_email": "owner@acme.test",
        }
        action = {"message": "Moved to <b>closed</b>"}

        captured: dict = {}

        async def fake_send_email(**kwargs):
            captured.update(kwargs)
            return {"success": True}

        with patch.object(pipeline_automations, "send_email", new=fake_send_email):
            asyncio.run(
                pipeline_automations._execute_notify_team_action(
                    action,
                    lead,
                    tenant,
                    new_stage="closed <won>",
                    old_stage="qualified & ready",
                )
            )

        body = captured["body_html"]
        subject = captured["subject"]

        # The raw malicious name must NOT appear verbatim
        assert malicious_name not in body, (
            "regression: lead name injected unescaped into email body "
            "(bug-patterns #71)"
        )
        assert "<img src=x" not in body

        # Entity-escaped versions must appear
        assert "&lt;img src=x onerror=alert(1)&gt;" in body
        assert "&lt;b&gt;closed&lt;/b&gt;" in body  # message escaped
        assert "qualified &amp; ready" in body  # old_stage escaped
        assert "closed &lt;won&gt;" in body  # new_stage escaped
        assert "Acme &lt;Corp&gt;" in subject  # business_name escaped
        assert "&lt;img src=x" in subject  # lead name escaped in subject too
