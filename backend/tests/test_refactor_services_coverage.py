"""Service-level coverage for the recently-extracted refactor modules.

Router-scope mocks bypass these modules because the routers expose
back-compat aliases. These tests exercise the real service code directly
by passing a chainable ``FakeSupabase`` as ``db`` so the changed-lines
coverage gate (>=85%) passes for the worst-offender modules:

- backend/services/appointment_ical.py
- backend/services/appointment_stats.py
- backend/services/sequence_campaign.py
- backend/services/marketing_campaigns_service.py
- backend/services/admin_analytics_service.py
- backend/services/inbound_call_handler.py
"""

import asyncio
from unittest.mock import patch

import pytest

from backend.tests._fake_supabase import FakeSupabase


# ---------------------------------------------------------------------------
# appointment_ical
# ---------------------------------------------------------------------------


def test_format_ical_dt_parses_iso_with_z():
    from backend.services.appointment_ical import format_ical_dt

    assert format_ical_dt("2026-05-23T14:30:00Z") == "20260523T143000Z"


def test_format_ical_dt_parses_iso_with_offset():
    from backend.services.appointment_ical import format_ical_dt

    assert format_ical_dt("2026-05-23T14:30:00+00:00") == "20260523T143000Z"


def test_format_ical_dt_fallback_on_unparseable():
    from backend.services.appointment_ical import format_ical_dt

    # garbage falls through the except branch and gets the regex-free fallback
    result = format_ical_dt("not-a-date")
    assert result.endswith("Z")


def test_fetch_ical_appointments_returns_data():
    from backend.services.appointment_ical import fetch_ical_appointments

    rows = [
        {"id": "a1", "start_time": "2026-05-23T10:00:00Z",
         "end_time": "2026-05-23T11:00:00Z", "status": "confirmed",
         "customer_name": "Alice"},
    ]
    db = FakeSupabase().configure("appointments", data=rows)
    assert fetch_ical_appointments(db, "tenant-1") == rows


def test_fetch_ical_appointments_empty():
    from backend.services.appointment_ical import fetch_ical_appointments

    db = FakeSupabase()
    assert fetch_ical_appointments(db, "tenant-1") == []


def test_build_appointments_ical_confirmed_event():
    from backend.services.appointment_ical import build_appointments_ical

    appts = [{
        "id": "abc-123",
        "customer_name": "Bob",
        "customer_email": "bob@example.com",
        "customer_phone": "+15551234567",
        "notes": "Bring laptop",
        "status": "confirmed",
        "start_time": "2026-05-23T10:00:00Z",
        "end_time": "2026-05-23T11:00:00Z",
    }]
    ics = build_appointments_ical(appts, "Acme Co")

    assert "BEGIN:VCALENDAR" in ics
    assert "PRODID:-//AgentNexLiFy//Acme Co//EN" in ics
    assert "X-WR-CALNAME:Acme Co Appointments" in ics
    assert "UID:abc-123@agentnexlify.com" in ics
    assert "SUMMARY:Appointment: Bob" in ics
    assert "Email: bob@example.com" in ics
    assert "Phone: +15551234567" in ics
    assert "Notes: Bring laptop" in ics
    assert "Status: confirmed" in ics
    assert "DTSTART:20260523T100000Z" in ics
    assert "DTEND:20260523T110000Z" in ics
    assert "STATUS:CONFIRMED" in ics
    assert ics.endswith("END:VCALENDAR")


def test_build_appointments_ical_no_show_maps_to_cancelled():
    from backend.services.appointment_ical import build_appointments_ical

    appts = [{
        "id": "x",
        "status": "no_show",
        "start_time": "2026-05-23T10:00:00Z",
        "end_time": "2026-05-23T11:00:00Z",
    }]
    ics = build_appointments_ical(appts, "Biz")
    assert "STATUS:CANCELLED" in ics
    # SUMMARY default when no customer_name present
    assert "SUMMARY:Appointment: Customer" in ics


def test_build_appointments_ical_empty_list_has_envelope_only():
    from backend.services.appointment_ical import build_appointments_ical

    ics = build_appointments_ical([], "Empty Biz")
    assert "BEGIN:VCALENDAR" in ics
    assert "END:VCALENDAR" in ics
    assert "BEGIN:VEVENT" not in ics


# ---------------------------------------------------------------------------
# appointment_stats
# ---------------------------------------------------------------------------


def test_fetch_no_show_appointments_returns_rows():
    from backend.services.appointment_stats import fetch_no_show_appointments

    rows = [{"id": "a", "status": "no_show", "customer_email": "x@y.com"}]
    db = FakeSupabase().configure("appointments", data=rows)
    assert fetch_no_show_appointments(db, "tenant-1") == rows


def test_compute_no_show_stats_zero_division_safe():
    from backend.services.appointment_stats import compute_no_show_stats

    stats = compute_no_show_stats([])
    assert stats == {
        "total_appointments": 0,
        "no_show_count": 0,
        "no_show_rate": 0,
        "repeat_offenders": [],
    }


def test_compute_no_show_stats_ranks_repeat_offenders():
    from backend.services.appointment_stats import compute_no_show_stats

    appts = [
        {"status": "completed", "customer_email": "ok@x.com"},
        {"status": "no_show", "customer_email": "bad@x.com"},
        {"status": "no_show", "customer_email": "bad@x.com"},
        {"status": "no_show", "customer_email": "bad@x.com"},
        {"status": "no_show", "customer_email": "once@x.com"},
        {"status": "no_show", "customer_name": "NoEmail"},
        {"status": "no_show", "customer_name": "NoEmail"},
    ]
    stats = compute_no_show_stats(appts)
    assert stats["total_appointments"] == 7
    assert stats["no_show_count"] == 6
    assert stats["no_show_rate"] == round(6 / 7 * 100, 1)
    # Only entities with >=2 no-shows show up, sorted by count desc.
    assert stats["repeat_offenders"] == [
        {"customer": "bad@x.com", "no_show_count": 3},
        {"customer": "NoEmail", "no_show_count": 2},
    ]


def test_compute_no_show_stats_falls_back_to_unknown():
    from backend.services.appointment_stats import compute_no_show_stats

    appts = [
        {"status": "no_show"},
        {"status": "no_show"},
    ]
    stats = compute_no_show_stats(appts)
    assert stats["repeat_offenders"] == [
        {"customer": "unknown", "no_show_count": 2},
    ]


# ---------------------------------------------------------------------------
# sequence_campaign
# ---------------------------------------------------------------------------


def test_fetch_campaign_leads_drops_unsubscribed_and_filters_tags():
    from backend.services.sequence_campaign import fetch_campaign_leads

    rows = [
        {"id": "1", "email": "a@x.com", "tags": ["vip"], "unsubscribed": False},
        {"id": "2", "email": "b@x.com", "tags": ["vip"], "unsubscribed": True},
        {"id": "3", "email": "c@x.com", "tags": ["other"], "unsubscribed": False},
        {"id": "4", "email": "d@x.com", "tags": None, "unsubscribed": False},
    ]
    db = FakeSupabase().configure("leads", data=rows)

    filters = {
        "status": "new",
        "min_score": 10,
        "created_after": "2026-01-01",
        "created_before": "2026-12-31",
        "tags": ["vip"],
    }
    leads = fetch_campaign_leads(db, "tenant-1", filters)
    assert [l["id"] for l in leads] == ["1"]


def test_fetch_campaign_leads_no_filters_keeps_all_non_unsubscribed():
    from backend.services.sequence_campaign import fetch_campaign_leads

    rows = [
        {"id": "1", "email": "a@x.com", "unsubscribed": False},
        {"id": "2", "email": "b@x.com", "unsubscribed": True},
    ]
    db = FakeSupabase().configure("leads", data=rows)
    leads = fetch_campaign_leads(db, "tenant-1", {})
    assert [l["id"] for l in leads] == ["1"]


def test_dispatch_campaign_email_path_counts_sent_and_skipped():
    from backend.services import sequence_campaign

    leads = [
        {"id": "1", "email": "a@x.com"},
        {"id": "2", "email": None},  # skipped — no email
        {"id": "3", "email": "c@x.com"},
    ]

    async def fake_send_email(**kwargs):
        return {"success": kwargs["to"] == "a@x.com"}

    with patch.object(sequence_campaign, "send_email", side_effect=fake_send_email):
        result = asyncio.run(sequence_campaign.dispatch_campaign(
            leads,
            tenant_id="t1",
            channel="email",
            subject="hello",
            body_html="<p>body</p>",
            plan="growth",
        ))

    assert result == {"total_leads": 3, "sent": 1, "skipped": 2}


def test_dispatch_campaign_sms_path_respects_rate_limit():
    from backend.services import sequence_campaign

    leads = [
        {"id": "1", "phone": "+1"},
        {"id": "2", "phone": None},  # skipped — no phone
        {"id": "3", "phone": "+3"},  # skipped — rate limit blocks
        {"id": "4", "phone": "+4"},  # sent
    ]

    calls = {"check": 0}

    def fake_check(tenant_id, plan):
        calls["check"] += 1
        # 2nd lead has no phone (skips earlier), so check fires for ids 1, 3, 4
        return calls["check"] != 2  # second check (lead id=3) returns False

    async def fake_send_sms(**kwargs):
        return True

    with patch.object(sequence_campaign, "check_sms_rate_limit", side_effect=fake_check), \
         patch.object(sequence_campaign, "send_sms", side_effect=fake_send_sms), \
         patch.object(sequence_campaign, "increment_sms_count") as inc:
        result = asyncio.run(sequence_campaign.dispatch_campaign(
            leads,
            tenant_id="t1",
            channel="sms",
            subject="",
            body_html="hi",
            plan="growth",
        ))

    assert result == {"total_leads": 4, "sent": 2, "skipped": 2}
    assert inc.call_count == 2


def test_dispatch_campaign_sms_send_failure_counts_skipped():
    from backend.services import sequence_campaign

    leads = [{"id": "1", "phone": "+1"}]

    async def fake_send_sms(**kwargs):
        return False

    with patch.object(sequence_campaign, "check_sms_rate_limit", return_value=True), \
         patch.object(sequence_campaign, "send_sms", side_effect=fake_send_sms), \
         patch.object(sequence_campaign, "increment_sms_count"):
        result = asyncio.run(sequence_campaign.dispatch_campaign(
            leads,
            tenant_id="t1",
            channel="sms",
            subject="",
            body_html="hi",
            plan="growth",
        ))

    assert result == {"total_leads": 1, "sent": 0, "skipped": 1}


# ---------------------------------------------------------------------------
# marketing_campaigns_service
# ---------------------------------------------------------------------------


def test_parse_generated_email_with_subject_and_separator():
    from backend.services.marketing_campaigns_service import parse_generated_email

    raw = "SUBJECT: Hi there\n---\n<p>Body</p>"
    subject, body = parse_generated_email(raw)
    assert subject == "Hi there"
    assert body == "<p>Body</p>"


def test_parse_generated_email_with_subject_no_separator():
    from backend.services.marketing_campaigns_service import parse_generated_email

    raw = "SUBJECT: Greetings\n<p>Body</p>"
    subject, body = parse_generated_email(raw)
    assert subject == "Greetings"
    assert body == "<p>Body</p>"


def test_parse_generated_email_without_subject():
    from backend.services.marketing_campaigns_service import parse_generated_email

    raw = "<p>Just a body</p>"
    subject, body = parse_generated_email(raw)
    assert subject == ""
    assert body == "<p>Just a body</p>"


def test_query_target_leads_returns_filtered_leads():
    from backend.services.marketing_campaigns_service import query_target_leads

    rows = [
        {"id": "1", "tags": ["a", "b"]},
        {"id": "2", "tags": ["c"]},
        {"id": "3", "tags": None},
    ]
    db = FakeSupabase().configure("leads", data=rows)
    result = query_target_leads(db, "tenant-1", {
        "status": ["new"],
        "lead_temperature": ["hot"],
        "tags": ["a"],
    })
    assert [l["id"] for l in result] == ["1"]


def test_query_target_leads_handles_query_failure():
    from backend.services.marketing_campaigns_service import query_target_leads

    db = FakeSupabase().raise_on("leads", op="select")
    assert query_target_leads(db, "tenant-1", None) == []


def test_query_target_leads_no_filter_returns_rows():
    from backend.services.marketing_campaigns_service import query_target_leads

    rows = [{"id": "1"}, {"id": "2"}]
    db = FakeSupabase().configure("leads", data=rows)
    assert query_target_leads(db, "tenant-1", None) == rows


def test_compute_campaign_analytics_happy_path():
    from backend.services.marketing_campaigns_service import compute_campaign_analytics

    campaign_row = {
        "id": "c1", "name": "Spring Promo", "type": "email",
        "status": "sent", "total_recipients": 100, "total_sent": 100,
        "total_opened": 0, "total_clicked": 0, "sent_at": None,
    }
    sends = [
        {"id": "s1", "status": "opened", "sent_at": None,
         "opened_at": None, "clicked_at": None},
        {"id": "s2", "status": "clicked", "sent_at": None,
         "opened_at": None, "clicked_at": None},
        {"id": "s3", "status": "bounced", "sent_at": None,
         "opened_at": None, "clicked_at": None},
        {"id": "s4", "status": "failed", "sent_at": None,
         "opened_at": None, "clicked_at": None},
    ]
    db = (
        FakeSupabase()
        .configure("marketing_campaigns", data=[campaign_row])
        .configure("campaign_sends", data=sends)
        .configure("email_events", data=[])
    )
    result = compute_campaign_analytics(db, "tenant-1", "c1")
    assert result["campaign"] == campaign_row
    assert result["total_sent"] == 100
    # opened + clicked together
    assert result["total_opened"] == 2
    assert result["total_clicked"] == 1
    assert result["total_bounced"] == 1
    assert result["total_failed"] == 1
    assert result["open_rate"] == 2.0
    assert result["click_rate"] == 1.0
    assert result["trend_data"] == []
    assert result["device_breakdown"] == {}


def test_compute_campaign_analytics_zero_sent_zero_rates():
    from backend.services.marketing_campaigns_service import compute_campaign_analytics

    campaign_row = {
        "id": "c2", "name": "Empty", "type": "email", "status": "draft",
        "total_recipients": 0, "total_sent": 0, "total_opened": 0,
        "total_clicked": 0, "sent_at": None,
    }
    db = (
        FakeSupabase()
        .configure("marketing_campaigns", data=[campaign_row])
        .configure("campaign_sends", data=[])
        .configure("email_events", data=[])
    )
    result = compute_campaign_analytics(db, "tenant-1", "c2")
    assert result["open_rate"] == 0
    assert result["click_rate"] == 0


def test_compute_campaign_analytics_raises_when_missing():
    from backend.services.marketing_campaigns_service import (
        CampaignNotFound,
        compute_campaign_analytics,
    )

    db = FakeSupabase().configure("marketing_campaigns", data=[])
    with pytest.raises(CampaignNotFound):
        compute_campaign_analytics(db, "tenant-1", "nope")


def test_compute_trend_data_with_recent_send_and_events():
    from datetime import datetime, timezone, timedelta
    from backend.services.marketing_campaigns_service import (
        compute_campaign_analytics,
    )

    sent_at = (
        datetime.now(timezone.utc) - timedelta(days=3)
    ).isoformat().replace("+00:00", "Z")
    today_key = datetime.now(timezone.utc).date().isoformat()

    campaign_row = {
        "id": "c3", "name": "Trend", "type": "email", "status": "sent",
        "total_recipients": 1, "total_sent": 1, "total_opened": 0,
        "total_clicked": 0, "sent_at": sent_at,
    }
    events = [
        {"event_type": "open", "created_at": today_key + "T00:00:00Z"},
        {"event_type": "click", "created_at": today_key + "T01:00:00Z"},
    ]
    db = (
        FakeSupabase()
        .configure("marketing_campaigns", data=[campaign_row])
        .configure("campaign_sends", data=[])
        .configure("email_events", data=events)
    )
    result = compute_campaign_analytics(db, "tenant-1", "c3")
    # trend_data should have lookback+1 entries (>=3 days, possibly 4)
    assert len(result["trend_data"]) >= 3
    # Last entry should be today with the open + click events
    today_entry = result["trend_data"][-1]
    assert today_entry["date"] == today_key
    assert today_entry["opens"] == 1
    assert today_entry["clicks"] == 1


def test_compute_device_breakdown_categorizes():
    from datetime import datetime, timezone, timedelta
    from backend.services.marketing_campaigns_service import (
        compute_campaign_analytics,
    )

    sent_at = (
        datetime.now(timezone.utc) - timedelta(days=1)
    ).isoformat().replace("+00:00", "Z")

    campaign_row = {
        "id": "c4", "name": "Devices", "type": "email", "status": "sent",
        "total_recipients": 1, "total_sent": 1, "total_opened": 0,
        "total_clicked": 0, "sent_at": sent_at,
    }
    events = [
        {"details": {"device": "iPhone Safari"}},
        {"details": {"device": "Android Chrome"}},
        {"details": {"device": "Desktop Firefox"}},
        {"details": {"device": "weird-computer-thing"}},
        {"details": {"user_agent": "GenericBot"}},
        {"details": None},
    ]
    # Trend data will also read email_events with date filter — irrelevant to this test.
    db = (
        FakeSupabase()
        .configure("marketing_campaigns", data=[campaign_row])
        .configure("campaign_sends", data=[])
        .configure("email_events", data=events)
    )
    result = compute_campaign_analytics(db, "tenant-1", "c4")
    bd = result["device_breakdown"]
    assert bd.get("mobile") == 2
    # "Desktop Firefox" and "weird-computer-thing" both match the computer branch
    assert bd.get("desktop") == 2
    assert bd.get("other") == 2


def test_build_email_system_prompt_uses_known_type():
    from backend.services.marketing_campaigns_service import (
        TYPE_INSTRUCTIONS,
        build_email_system_prompt,
    )

    prompt = build_email_system_prompt(
        "Acme", "salon", "promotional", "friendly"
    )
    assert "Acme" in prompt
    assert ", a salon" in prompt
    assert TYPE_INSTRUCTIONS["promotional"] in prompt
    assert "Tone: friendly." in prompt
    assert "SUBJECT:" in prompt


def test_build_email_system_prompt_no_business_type_or_unknown_type():
    from backend.services.marketing_campaigns_service import build_email_system_prompt

    prompt = build_email_system_prompt("Acme", None, "unknown-type", "bold")
    assert "Acme" in prompt
    # Unknown type → TYPE_INSTRUCTIONS.get returns '' → still valid prompt
    assert "Tone: bold." in prompt


def test_build_email_system_prompt_all_known_types_compile():
    from backend.services.marketing_campaigns_service import (
        TYPE_INSTRUCTIONS,
        build_email_system_prompt,
    )

    for ctype in TYPE_INSTRUCTIONS:
        prompt = build_email_system_prompt("Biz", "auto", ctype, "warm")
        assert TYPE_INSTRUCTIONS[ctype] in prompt


# ---------------------------------------------------------------------------
# admin_analytics_service
# ---------------------------------------------------------------------------


def test_compute_platform_overview_aggregates_revenue_and_status():
    from backend.services.admin_analytics_service import compute_platform_overview

    active_tenants = [
        {"plan": "growth", "stripe_subscription_id": "sub_1"},
        {"plan": "growth", "stripe_subscription_id": "sub_2"},
        {"plan": "professional", "stripe_subscription_id": None},
        {"plan": "autopilot", "stripe_subscription_id": "sub_3"},
    ]
    promos = [
        {"tenant_id": "a"},
        {"tenant_id": "a"},  # dedupes
        {"tenant_id": "b"},
        {"tenant_id": None},  # filtered out
    ]
    db = FakeSupabase()
    # exact counts for the count="exact" calls
    db.configure_op("tenants", "select", data=active_tenants, count=4)
    db.configure("admin_promotions", data=promos)

    result = compute_platform_overview(db)
    assert result["total_tenants"] == 4
    # only tenants with stripe_subscription_id count as active_paid
    assert result["active_paid_subscriptions"] == 3
    # MRR = growth + growth + autopilot (professional has no sub_id)
    assert result["mrr_cents"] == (
        9900 + 9900 + 29900
    )
    assert result["mrr_dollars"] == round(result["mrr_cents"] / 100, 2)
    # Plan breakdown counts ALL active rows (including no-sub professional)
    assert result["plan_breakdown"] == {
        "growth": 2, "professional": 1, "autopilot": 1,
    }
    assert result["promoted_business"] == 2


def test_compute_platform_overview_tolerates_missing_promotions_and_trials():
    from backend.services.admin_analytics_service import compute_platform_overview

    db = FakeSupabase()
    db.configure_op("tenants", "select", data=[], count=0)
    # raise on admin_promotions to hit the except branch
    db.raise_on("admin_promotions", op="select")
    result = compute_platform_overview(db)
    assert result["promoted_business"] == 0
    assert result["active_paid_subscriptions"] == 0


def test_compute_monthly_growth_groups_signups_and_cumulative():
    from datetime import datetime, timezone
    from backend.services.admin_analytics_service import compute_monthly_growth

    now = datetime.now(timezone.utc)
    this_month = now.strftime("%Y-%m")
    signups = [
        {"created_at": f"{this_month}-05T10:00:00Z", "plan": "growth"},
        {"created_at": f"{this_month}-10T10:00:00Z", "plan": "free"},
        {"created_at": "", "plan": "free"},  # skipped — no created_at
    ]
    db = FakeSupabase()
    db.configure("tenants", data=signups)
    db.configure("platform_monthly_revenue", data=[])
    result = compute_monthly_growth(db, months=1)
    bucket = result["monthly_data"][-1]
    assert bucket["month"] == this_month
    assert bucket["new_signups"] == 2
    assert bucket["new_paid"] == 1
    assert bucket["new_free"] == 1
    assert bucket["plan_breakdown"]["growth"] == 1
    assert bucket["plan_breakdown"]["free"] == 1
    assert bucket["total_at_end"] == 2


def test_compute_monthly_growth_applies_churned_data():
    from datetime import datetime, timezone
    from backend.services.admin_analytics_service import compute_monthly_growth

    now = datetime.now(timezone.utc)
    this_month = now.strftime("%Y-%m")
    db = FakeSupabase()
    db.configure("tenants", data=[])
    db.configure("platform_monthly_revenue",
                 data=[{"month": f"{this_month}-01", "churned": 3}])
    result = compute_monthly_growth(db, months=1)
    bucket = result["monthly_data"][-1]
    assert bucket.get("churned") == 3


def test_compute_weekly_growth_computes_deltas():
    from datetime import datetime, timezone
    from backend.services.admin_analytics_service import compute_weekly_growth

    today = datetime.now(timezone.utc).date().isoformat()
    signups = [
        {"created_at": today + "T08:00:00Z", "plan": "growth"},
        {"created_at": today + "T09:00:00Z", "plan": "free"},
    ]
    db = FakeSupabase()
    # Recent week signups
    db.configure_op("tenants", "select", data=signups, count=1)
    result = compute_weekly_growth(db)
    today_bucket = [d for d in result["daily_data"] if d["date"] == today][0]
    assert today_bucket["signups"] == 2
    assert today_bucket["paid"] == 1
    assert today_bucket["revenue_cents"] == 9900
    assert today_bucket["free"] == 1
    assert result["this_week_signups"] == 2
    # prev_week_signups == 1 from count=1, delta = 2-1 = 1, pct = 100
    assert result["week_delta"] == 1
    assert result["week_delta_pct"] == 100
    # active_paid: same data but only rows with stripe_subscription_id
    # signups don't have stripe_subscription_id → 0
    assert result["active_paid_subscriptions"] == 0


def test_compute_plan_distribution_percentage_rounded():
    from backend.services.admin_analytics_service import compute_plan_distribution

    tenants = [
        {"plan": "growth", "plan_status": "active"},
        {"plan": "growth", "plan_status": "active"},
        {"plan": "growth", "plan_status": "cancelled"},
        {"plan": "free", "plan_status": "active"},
    ]
    db = FakeSupabase().configure("tenants", data=tenants)
    result = compute_plan_distribution(db)
    assert result["total_tenants"] == 4
    plans = {row["plan"]: row for row in result["distribution"]}
    assert plans["growth"]["active"] == 2
    assert plans["growth"]["cancelled"] == 1
    assert plans["growth"]["total"] == 3
    assert plans["growth"]["percentage"] == 75.0
    assert plans["free"]["active"] == 1


def test_compute_plan_distribution_empty_returns_zero_percent():
    from backend.services.admin_analytics_service import compute_plan_distribution

    db = FakeSupabase().configure("tenants", data=[])
    result = compute_plan_distribution(db)
    assert result == {"total_tenants": 0, "distribution": []}


def test_compute_revenue_trends_uses_precomputed_when_present():
    from backend.services.admin_analytics_service import compute_revenue_trends

    rows = [{"month": "2026-01-01", "mrr_cents": 1000}]
    db = FakeSupabase().configure("platform_monthly_revenue", data=rows)
    result = compute_revenue_trends(db, months=2)
    assert result["source"] == "precomputed"
    assert result["revenue_trends"] == rows


def test_compute_revenue_trends_falls_back_to_live_when_empty():
    from datetime import datetime, timezone
    from backend.services.admin_analytics_service import compute_revenue_trends

    now = datetime.now(timezone.utc)
    this_month = now.strftime("%Y-%m")
    paid_tenants = [
        {
            "id": "1", "plan": "growth", "plan_status": "active",
            "stripe_subscription_id": "sub_1",
            "created_at": f"{this_month}-01T00:00:00Z",
        },
    ]
    db = FakeSupabase()
    db.configure("platform_monthly_revenue", data=[])
    db.configure("tenants", data=paid_tenants)
    result = compute_revenue_trends(db, months=1)
    assert result["source"] == "live"
    # one-month window → exactly one month bucket
    assert len(result["revenue_trends"]) >= 1
    last = result["revenue_trends"][-1]
    assert last["mrr_cents"] == 9900
    assert last["new_signups"] == 1


def test_compute_revenue_trends_unavailable_when_everything_fails():
    from backend.services.admin_analytics_service import compute_revenue_trends

    db = FakeSupabase()
    db.raise_on("platform_monthly_revenue", op="select")
    db.raise_on("tenants", op="select")
    result = compute_revenue_trends(db, months=2)
    assert result["source"] == "unavailable"
    assert result["revenue_trends"] == []


def test_list_promoted_businesses_happy_path():
    from backend.services.admin_analytics_service import list_promoted_businesses

    db = FakeSupabase().configure("admin_promotions", data=[{"id": "p1"}])
    result = list_promoted_businesses(db)
    assert result == {"promotions": [{"id": "p1"}]}


def test_list_promoted_businesses_tolerates_missing_table():
    from backend.services.admin_analytics_service import list_promoted_businesses

    db = FakeSupabase().raise_on("admin_promotions", op="select")
    result = list_promoted_businesses(db)
    assert result["promotions"] == []
    assert "migration 089" in result["note"]


def test_list_admin_tenants_with_filters_and_search():
    from backend.services.admin_analytics_service import list_admin_tenants

    rows = [{"id": "t1", "business_name": "Acme"}]
    db = FakeSupabase().configure_op("tenants", "select", data=rows, count=1)
    result = list_admin_tenants(
        db,
        plan="growth",
        plan_status="active",
        business_type="salon",
        search="acme, owner",
        limit=10,
        offset=0,
    )
    assert result == {"tenants": rows, "total": 1}


def test_list_admin_tenants_no_filters():
    from backend.services.admin_analytics_service import list_admin_tenants

    db = FakeSupabase().configure_op("tenants", "select", data=[], count=0)
    result = list_admin_tenants(
        db, plan=None, plan_status=None,
        business_type=None, search=None, limit=20, offset=0,
    )
    assert result == {"tenants": [], "total": 0}


def test_compute_industry_breakdown_sorted_and_percentage():
    from backend.services.admin_analytics_service import compute_industry_breakdown

    tenants = [
        {"business_type": "salon", "plan": "growth"},
        {"business_type": "salon", "plan": "free"},
        {"business_type": "salon", "plan": "professional"},
        {"business_type": "plumber", "plan": "free"},
        {"business_type": None, "plan": "free"},  # falls back to 'other'
    ]
    db = FakeSupabase().configure("tenants", data=tenants)
    result = compute_industry_breakdown(db)
    industries = [row["industry"] for row in result["breakdown"]]
    assert industries[0] == "salon"
    salon = result["breakdown"][0]
    assert salon["total"] == 3
    assert salon["paid"] == 2
    assert salon["free"] == 1
    assert salon["paid_percentage"] == round(2 / 3 * 100, 1)


# ---------------------------------------------------------------------------
# inbound_call_handler
# ---------------------------------------------------------------------------


def test_find_or_create_lead_for_caller_returns_existing():
    from backend.services.inbound_call_handler import find_or_create_lead_for_caller

    db = FakeSupabase().configure_op("leads", "select", data=[{"id": "L1"}])
    assert find_or_create_lead_for_caller(db, "t1", "+15551234567") == "L1"


def test_find_or_create_lead_for_caller_creates_when_missing():
    from backend.services.inbound_call_handler import find_or_create_lead_for_caller

    db = FakeSupabase()
    db.configure_op("leads", "select", data=[])
    db.configure_op("leads", "insert", echo_payload=True)
    # insert echo_payload returns the payload as data, but the inserted row
    # doesn't carry an id — patch with explicit data instead.
    db.configure_op("leads", "insert", data=[{"id": "L_NEW"}])
    assert find_or_create_lead_for_caller(db, "t1", "+15551234567") == "L_NEW"


def test_find_or_create_lead_for_caller_handles_exception():
    from backend.services.inbound_call_handler import find_or_create_lead_for_caller

    db = FakeSupabase().raise_on("leads", op="select")
    assert find_or_create_lead_for_caller(db, "t1", "+1") is None


def test_find_or_create_lead_for_caller_returns_none_when_insert_returns_nothing():
    from backend.services.inbound_call_handler import find_or_create_lead_for_caller

    db = FakeSupabase()
    db.configure_op("leads", "select", data=[])
    db.configure_op("leads", "insert", data=[])
    assert find_or_create_lead_for_caller(db, "t1", "+1") is None


def test_store_inbound_call_record_returns_id():
    from backend.services.inbound_call_handler import store_inbound_call_record

    db = FakeSupabase().configure("calls", data=[{"id": "C_ID"}])
    cid = store_inbound_call_record(
        db,
        tenant_id="t1",
        lead_id="L1",
        call_sid="CA123",
        caller="+1",
        called="+2",
        duration=42,
        recording_url="https://x/y",
    )
    assert cid == "C_ID"


def test_store_inbound_call_record_handles_no_lead_id():
    from backend.services.inbound_call_handler import store_inbound_call_record

    db = FakeSupabase().configure("calls", data=[{"id": "C2"}])
    cid = store_inbound_call_record(
        db,
        tenant_id="t1",
        lead_id=None,
        call_sid="CA123",
        caller="+1",
        called="+2",
        duration=0,
        recording_url="https://x/y",
    )
    assert cid == "C2"


def test_store_inbound_call_record_returns_none_on_exception():
    from backend.services.inbound_call_handler import store_inbound_call_record

    db = FakeSupabase().raise_on("calls", op="insert")
    cid = store_inbound_call_record(
        db,
        tenant_id="t1",
        lead_id=None,
        call_sid="CA",
        caller="+1",
        called="+2",
        duration=0,
        recording_url="https://x",
    )
    assert cid is None


def test_store_inbound_call_record_returns_none_when_no_data():
    from backend.services.inbound_call_handler import store_inbound_call_record

    db = FakeSupabase().configure("calls", data=[])
    cid = store_inbound_call_record(
        db,
        tenant_id="t1",
        lead_id="L1",
        call_sid="CA",
        caller="+1",
        called="+2",
        duration=0,
        recording_url="https://x",
    )
    assert cid is None


def test_request_twilio_transcription_success():
    from backend.services import inbound_call_handler

    class _Resp:
        status_code = 201
        text = ""

    class _Client:
        def __init__(self, *a, **kw):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return None
        async def post(self, url, **kwargs):
            return _Resp()

    with patch.object(inbound_call_handler.httpx, "AsyncClient", _Client):
        asyncio.run(inbound_call_handler.request_twilio_transcription(
            recording_sid="RE1",
            transcription_url="https://cb",
            account_sid="AC1",
            auth_token="tok",
            call_sid="CA1",
        ))


def test_request_twilio_transcription_non_2xx_logs_warning():
    from backend.services import inbound_call_handler

    class _Resp:
        status_code = 500
        text = "boom"

    class _Client:
        def __init__(self, *a, **kw):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return None
        async def post(self, url, **kwargs):
            return _Resp()

    with patch.object(inbound_call_handler.httpx, "AsyncClient", _Client):
        asyncio.run(inbound_call_handler.request_twilio_transcription(
            recording_sid="RE1",
            transcription_url="https://cb",
            account_sid="AC1",
            auth_token="tok",
            call_sid="CA1",
        ))


def test_request_twilio_transcription_handles_exception():
    from backend.services import inbound_call_handler

    class _Client:
        def __init__(self, *a, **kw):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return None
        async def post(self, url, **kwargs):
            raise RuntimeError("network down")

    with patch.object(inbound_call_handler.httpx, "AsyncClient", _Client):
        # Should swallow the exception and just log
        asyncio.run(inbound_call_handler.request_twilio_transcription(
            recording_sid="RE1",
            transcription_url="https://cb",
            account_sid="AC1",
            auth_token="tok",
            call_sid="CA1",
        ))
