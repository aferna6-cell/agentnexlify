"""Weekly conversion-rate metrics in compute_funnel() (2026-08-25).

msg_to_lead_rate_week and lead_to_appt_rate_week keep the shipped 2026-06
conversion fixes measurable every week (audit-post-deploy-measurement series)
instead of requiring a manual prod-query pass.

Contract:
  - new_messages_week counts this week's chat_messages from real tenants
  - rates are percent floats rounded to 1 decimal
  - rate is None when the denominator is 0 or a source metric failed
  - chat_messages is now queried twice (activated, then new_messages_week)

Run with:
    pytest backend/tests/test_funnel_conversion_rates.py --noconftest -v
"""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

_THIS_WEEK = "2099-01-06T00:00:00+00:00"


class _FakeChain:
    def __init__(self, data=None, raise_on_execute=False):
        self._data = data if data is not None else []
        self._raise = raise_on_execute

    def select(self, *_, **__):
        return self

    def eq(self, *_):
        return self

    def neq(self, *_):
        return self

    def in_(self, *_):
        return self

    def gte(self, *_):
        return self

    def limit(self, *_):
        return self

    def execute(self):
        if self._raise:
            raise RuntimeError("simulated DB failure")
        result = MagicMock()
        result.data = self._data
        return result


def _tenant(tid):
    return {
        "id": tid,
        "business_name": "Acme Plumbing",
        "plan": "agent_os",
        "plan_status": "active",
        "created_at": _THIS_WEEK,
    }


def _make_db(
    *,
    tenant_rows,
    activated_msgs=None,
    week_msgs=None,
    with_leads=None,
    week_leads=None,
    week_appts=None,
    raise_week_msgs=False,
    raise_week_leads=False,
    raise_week_appts=False,
):
    """compute_funnel table() order:
    tenants → chat_messages (activated) → leads (with_leads) →
    appointments (with_appointments) → leads (week) → appointments (week) →
    chat_messages (week).

    Routing is by per-table call counters, so exact global order between
    tables does not matter.
    """
    msgs_calls = [0]
    leads_calls = [0]
    appts_calls = [0]

    def _router(name):
        if name == "tenants":
            return _FakeChain(data=tenant_rows)
        if name == "chat_messages":
            msgs_calls[0] += 1
            if msgs_calls[0] == 1:
                return _FakeChain(data=activated_msgs or [])
            return _FakeChain(data=week_msgs or [], raise_on_execute=raise_week_msgs)
        if name == "leads":
            leads_calls[0] += 1
            if leads_calls[0] == 1:
                return _FakeChain(data=with_leads or [])
            return _FakeChain(data=week_leads or [], raise_on_execute=raise_week_leads)
        if name == "appointments":
            appts_calls[0] += 1
            if appts_calls[0] == 1:
                return _FakeChain(data=[])
            return _FakeChain(data=week_appts or [], raise_on_execute=raise_week_appts)
        return _FakeChain(data=[])

    db = MagicMock()
    db.table.side_effect = _router
    return db


def _call(db):
    from backend.services.funnel_metrics import compute_funnel

    with patch(
        "backend.services.funnel_metrics.get_service_supabase", return_value=db
    ):
        return compute_funnel()


class TestNewMessagesWeek:
    def test_counts_real_tenant_messages(self):
        db = _make_db(
            tenant_rows=[_tenant("t1")],
            week_msgs=[
                {"tenant_id": "t1", "created_at": _THIS_WEEK},
                {"tenant_id": "t1", "created_at": _THIS_WEEK},
                {"tenant_id": "ghost", "created_at": _THIS_WEEK},  # not a real tenant
            ],
        )
        data = _call(db)
        assert data["new_messages_week"] == 2

    def test_failure_populates_errors_and_zeroes(self):
        db = _make_db(tenant_rows=[_tenant("t1")], raise_week_msgs=True)
        data = _call(db)
        assert data["new_messages_week"] == 0
        assert "new_messages_week" in data["errors"]


class TestMsgToLeadRate:
    def test_rate_computed(self):
        db = _make_db(
            tenant_rows=[_tenant("t1")],
            week_msgs=[{"tenant_id": "t1", "created_at": _THIS_WEEK}] * 200,
            week_leads=[{"client_id": "t1", "created_at": _THIS_WEEK}] * 17,
        )
        data = _call(db)
        assert data["msg_to_lead_rate_week"] == 8.5  # 17/200

    def test_none_when_zero_messages(self):
        db = _make_db(tenant_rows=[_tenant("t1")])
        data = _call(db)
        assert data["msg_to_lead_rate_week"] is None

    def test_none_when_messages_query_failed(self):
        db = _make_db(
            tenant_rows=[_tenant("t1")],
            week_leads=[{"client_id": "t1", "created_at": _THIS_WEEK}],
            raise_week_msgs=True,
        )
        data = _call(db)
        assert data["msg_to_lead_rate_week"] is None


class TestLeadToApptRate:
    def test_rate_computed(self):
        db = _make_db(
            tenant_rows=[_tenant("t1")],
            week_leads=[{"client_id": "t1", "created_at": _THIS_WEEK}] * 19,
            week_appts=[{"tenant_id": "t1", "created_at": _THIS_WEEK}] * 3,
        )
        data = _call(db)
        assert data["lead_to_appt_rate_week"] == 15.8  # 3/19

    def test_none_when_zero_leads(self):
        db = _make_db(
            tenant_rows=[_tenant("t1")],
            week_appts=[{"tenant_id": "t1", "created_at": _THIS_WEEK}],
        )
        data = _call(db)
        assert data["lead_to_appt_rate_week"] is None

    def test_none_when_appts_query_failed(self):
        db = _make_db(
            tenant_rows=[_tenant("t1")],
            week_leads=[{"client_id": "t1", "created_at": _THIS_WEEK}],
            raise_week_appts=True,
        )
        data = _call(db)
        assert data["lead_to_appt_rate_week"] is None


class TestWeeklyReportRendersRates:
    def test_report_shows_rates_and_messages(self):
        from backend.services.weekly_funnel_report import _build_report_html

        html = _build_report_html(
            {
                "total_tenants": 5,
                "new_messages_week": 200,
                "new_leads_week": 17,
                "new_appointments_week": 3,
                "msg_to_lead_rate_week": 8.5,
                "lead_to_appt_rate_week": 17.6,
            }
        )
        assert "Chat messages this week" in html
        assert "8.5%" in html
        assert "17.6%" in html

    def test_report_shows_na_when_rate_none(self):
        from backend.services.weekly_funnel_report import _build_report_html

        html = _build_report_html({"msg_to_lead_rate_week": None})
        assert "n/a" in html
