"""Tenant knowledge feed contracts (os_kb_feed -> SharedContext.kb)."""

from backend.services import os_kb_feed as feed


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        return _Result(self._rows)


def _patch_tables(monkeypatch, rows_by_table):
    monkeypatch.setattr(
        feed,
        "tenant_table",
        lambda _db, table, _cid: _Query(rows_by_table.get(table, [])),
    )


def test_vertical_guidance_maps_aliases_and_defaults():
    assert feed.vertical_guidance("auto_shop") == feed.VERTICAL_GUIDANCE["auto_repair"]
    assert feed.vertical_guidance("HVAC") == feed.VERTICAL_GUIDANCE["home_services"]
    assert feed.vertical_guidance("barbershop") == feed.VERTICAL_GUIDANCE["salon"]
    assert feed.vertical_guidance(None) == feed.VERTICAL_GUIDANCE["_default"]
    assert feed.vertical_guidance("yoga_studio") == feed.VERTICAL_GUIDANCE["_default"]


def test_tenant_kb_combines_guidance_faqs_and_website(monkeypatch):
    _patch_tables(
        monkeypatch,
        {
            "faq_entries": [
                {"question": "Do you do brakes?", "answer": "Yes, pads and rotors."},
                {"question": "Hours?", "answer": "Mon-Fri 8-6."},
                {"question": "", "answer": "skipped"},  # incomplete rows dropped
            ],
            "website_content": [
                {
                    "url": "https://sunsetauto.com",
                    "extracted_text": "Family-owned shop since 1998. " * 100,
                    "crawl_status": "completed",
                }
            ],
        },
    )
    entries = feed.tenant_kb_entries(object(), "t1", "auto_repair")
    topics = [e["topic"] for e in entries]

    # vertical guidance leads
    assert topics[0].startswith("industry:")
    # FAQs shaped as KbEntry
    assert {"topic": "Do you do brakes?", "answer": "Yes, pads and rotors."} in entries
    # incomplete FAQ dropped
    assert all(e["topic"] for e in entries)
    # website entry present and capped
    site = next(e for e in entries if e["topic"].startswith("website:"))
    assert len(site["answer"]) <= 1200


def test_tenant_kb_survives_total_db_failure(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("db down")

    monkeypatch.setattr(feed, "tenant_table", boom)
    entries = feed.tenant_kb_entries(object(), "t1", "salon")
    # guidance still returned; db-backed layers skipped, never raises
    assert entries == feed.VERTICAL_GUIDANCE["salon"]


def test_ai_usage_status_shapes_and_thresholds(monkeypatch):
    """rubric 5.3 — the usage surface reports spend vs guard thresholds."""
    from backend.services import ai_usage_guard as guard

    class _Q:
        def __init__(self, rows):
            self._rows = rows

        def select(self, *_a, **_k):
            return self

        def eq(self, *_a, **_k):
            return self

        def limit(self, *_a, **_k):
            return self

        def execute(self):
            class R:  # noqa: N801 - tiny local result shim
                pass

            r = R()
            r.data = self._rows
            return r

    class _DB:
        def __init__(self, tenants, usage):
            self._t, self._u = tenants, usage

        def table(self, name):
            return _Q(self._t if name == "tenants" else self._u)

    db = _DB(
        tenants=[{"ai_monthly_token_alert_threshold": 1000, "ai_monthly_token_hard_limit": 2000}],
        usage=[{"input_tokens": 900, "output_tokens": 200,
                "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}],
    )
    out = guard.get_ai_usage_status(db, "t1")
    assert out["total_tokens"] == 1100
    assert out["alert_reached"] is True
    assert out["hard_limit_reached"] is False

    class _Boom:
        def table(self, _):
            raise RuntimeError("down")

    safe = guard.get_ai_usage_status(_Boom(), "t1")
    assert safe["hard_limit_reached"] is False and safe["total_tokens"] == 0


def test_thin_knowledge_emits_gap_nudge():
    """Express-path self-healing: empty crawl + no FAQs -> staff is told
    which basics to gather from the owner, conversationally."""
    from unittest.mock import MagicMock

    db = MagicMock()
    empty = MagicMock(data=[])
    # tenant_table chains (faq_entries, website_content) return no rows
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = empty

    def fake_tenant_table(_db, _table, _cid):
        return chain

    import backend.services.os_kb_feed as feed_mod

    orig = feed_mod.tenant_table
    feed_mod.tenant_table = fake_tenant_table
    try:
        # tenants row missing city/phone/services; no business_hours row
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"city": "", "phone": "", "business_services": []}]
        )
        entries = feed_mod.tenant_kb_entries(db, "t1", "salon")
    finally:
        feed_mod.tenant_table = orig

    gap = [e for e in entries if "setup gaps" in e["topic"]]
    assert len(gap) == 1
    assert "services" in gap[0]["answer"]
    assert "ONE of these" in gap[0]["answer"]


def test_healthy_knowledge_emits_no_gap_nudge():
    from unittest.mock import MagicMock

    db = MagicMock()
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain

    def fake_tenant_table(_db, table, _cid):
        if table == "faq_entries":
            chain.execute.return_value = MagicMock(
                data=[{"question": f"q{i}", "answer": "a"} for i in range(5)]
            )
        else:
            chain.execute.return_value = MagicMock(
                data=[{"url": "https://x.com", "extracted_text": "lots of text", "crawl_status": "completed"}]
            )
        return chain

    import backend.services.os_kb_feed as feed_mod

    orig = feed_mod.tenant_table
    feed_mod.tenant_table = fake_tenant_table
    try:
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"city": "Austin", "phone": "555", "business_services": ["cuts"]}]
        )
        entries = feed_mod.tenant_kb_entries(db, "t1", "salon")
    finally:
        feed_mod.tenant_table = orig

    assert not [e for e in entries if "setup gaps" in e["topic"]]


def test_home_services_vertical_guidance():
    """Home-services depth: all trade aliases hit the home pack, which must
    carry emergency triage (incl. the gas-smell safety line), quoting
    discipline, and maintenance-plan guidance."""
    import backend.services.os_kb_feed as feed_mod

    for alias in ("plumbing", "hvac", "roofing", "electrical", "landscaping", "contractor", "home_services"):
        entries = feed_mod.vertical_guidance(alias)
        assert entries == feed_mod.VERTICAL_GUIDANCE["home_services"], alias

    topics = " ".join(e["topic"] for e in feed_mod.VERTICAL_GUIDANCE["home_services"])
    assert "emergency triage" in topics
    assert "quoting discipline" in topics
    assert "maintenance plans" in topics
    answers = " ".join(e["answer"] for e in feed_mod.VERTICAL_GUIDANCE["home_services"])
    # Safety invariant: gas smell -> leave the house, utility/911 before us
    assert "gas smell" in answers
    assert "911" in answers
    assert len(feed_mod.VERTICAL_GUIDANCE["home_services"]) >= 6


def test_financial_services_vertical_guidance():
    """G8: MTOptions vertical — trading aliases hit the financial pack,
    which must carry the no-financial-advice compliance entry."""
    import backend.services.os_kb_feed as feed_mod

    for alias in ("financial_services", "trading", "trading_alerts", "investing"):
        entries = feed_mod.vertical_guidance(alias)
        topics = " ".join(e["topic"] for e in entries)
        assert "compliance" in topics, alias
        answers = " ".join(e["answer"] for e in entries)
        assert "not personalized" in answers.lower() or "NOT personalized" in answers
