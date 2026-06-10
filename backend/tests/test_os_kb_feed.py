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
