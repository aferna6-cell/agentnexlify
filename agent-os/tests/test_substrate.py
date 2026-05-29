"""The data substrate: business profile, shared context, LLM provider state,
the offline SEO checker, and wishlist capture.
"""

from __future__ import annotations

from datetime import date

from agent_os.context import SharedContext
from agent_os.llm import (
    AnthropicProvider,
    DeterministicProvider,
    default_provider,
)
from agent_os.profile import CORE_FIELDS, BusinessProfile, KBEntry
from agent_os.tools.seo_check import seo_check
from agent_os.wishlist import Wishlist


# --------------------------------------------------------------------------- #
# BusinessProfile                                                             #
# --------------------------------------------------------------------------- #
def test_value_returns_none_for_blank():
    p = BusinessProfile(business_name="  ")
    assert p.value("business_name") is None
    assert p.has("business_name") is False


def test_value_joins_list_fields():
    p = BusinessProfile(services=["oil", "brakes"])
    assert p.value("services") == "oil, brakes"


def test_present_and_missing_core_fields():
    p = BusinessProfile(business_name="Bright Auto", phone="512-555-0100")
    assert set(p.present_core_fields()) == {"business_name", "phone"}
    assert "owner_name" in p.missing_core_fields()


def test_loaded_summary_is_none_when_empty():
    assert BusinessProfile().loaded_summary() is None


def test_loaded_summary_reflects_real_data():
    p = BusinessProfile(business_name="Bright Auto", hours="Mon–Fri")
    summary = p.loaded_summary()
    assert summary is not None
    assert "business name" in summary
    assert "hours" in summary


def test_signoff_prefers_name_and_business():
    assert BusinessProfile(owner_name="Sam", business_name="Bright Auto").signoff() == (
        "Sam, Bright Auto"
    )
    assert BusinessProfile(owner_name="Sam").signoff() == "Sam"
    assert BusinessProfile().signoff() == ""


def test_domain_strips_scheme():
    assert BusinessProfile(website="https://brightauto.com/").domain == "brightauto.com"
    assert BusinessProfile().domain is None


def test_core_fields_are_real_attributes():
    p = BusinessProfile()
    for field_name in CORE_FIELDS:
        assert hasattr(p, field_name)


def test_kb_entry_holds_topics():
    entry = KBEntry(question="Hours?", answer="9-5", topics=("hours",))
    assert entry.topics == ("hours",)


# --------------------------------------------------------------------------- #
# SharedContext query helpers                                                 #
# --------------------------------------------------------------------------- #
def test_context_widget_search(context: SharedContext):
    hits = context.widget_search("hybrid")
    assert hits
    assert any("hybrid" in c.summary.lower() or "hybrid" in c.topics for c in hits)


def test_context_lead_for(context: SharedContext):
    mike = context.lead_for("mike")
    assert mike is not None
    assert mike.quote_amount == 1100.0


def test_context_stale_leads(context: SharedContext):
    stale = context.stale_leads()
    assert [lead.name for lead in stale] == ["Dana"]


def test_context_appointments_on(context: SharedContext):
    today = context.appointments_on(date(2026, 5, 28))
    assert [a.customer_name for a in today] == ["Carlos"]


def test_empty_context_is_honestly_empty():
    ctx = SharedContext()
    assert ctx.widget_search("anything") == []
    assert ctx.lead_for("nobody") is None
    assert ctx.stale_leads() == []


# --------------------------------------------------------------------------- #
# LLM provider                                                                #
# --------------------------------------------------------------------------- #
def test_deterministic_provider_returns_fallback():
    p = DeterministicProvider()
    resp = p.complete(system="s", prompt="p", fallback="FALLBACK")
    assert resp.text == "FALLBACK"
    assert resp.live is False
    assert p.available is True


def test_deterministic_provider_can_simulate_outage():
    assert DeterministicProvider(available=False).available is False


def test_anthropic_provider_unavailable_without_key():
    assert AnthropicProvider(api_key=None).available is False


def test_default_provider_offline(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert isinstance(default_provider(), DeterministicProvider)


# --------------------------------------------------------------------------- #
# Offline SEO checker — fails honestly                                        #
# --------------------------------------------------------------------------- #
def test_seo_check_fails_honestly_on_bad_host():
    report = seo_check("http://nonexistent.invalid.localhost.example")
    assert report.fetched is False
    assert report.findings == []
    assert report.domain  # domain still extracted


def test_seo_check_extracts_domain():
    # ``.invalid`` never resolves (RFC 6761) → fast, offline-safe failure, but
    # the domain is still parsed from the URL before any fetch is attempted.
    report = seo_check("https://shop.example.invalid/contact")
    assert report.domain == "shop.example.invalid"
    assert report.fetched is False


# --------------------------------------------------------------------------- #
# Wishlist                                                                    #
# --------------------------------------------------------------------------- #
def test_wishlist_captures_with_closest_match():
    wl = Wishlist()
    entry = wl.capture("hire a technician", closest_agent_id="generalist", closest_score=0.3)
    assert entry.ask_text == "hire a technician"
    assert entry.closest_agent_id == "generalist"
    assert len(wl) == 1
    assert list(wl)[0] is entry
