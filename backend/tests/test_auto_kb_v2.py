"""TDD: Onboarding v2 auto-KB contract.

Existing POST /api/v1/onboarding/{tenant_id}/auto-kb returns:
  knowledge_base, custom_instructions, faqs[], pages_crawled, chars_extracted

Onboarding v2 spec adds wizard-pre-fill fields:
  services: list[str]  - extracted/seeded
  hours: dict[day, str]  - Mon-Sun keys for visual grid
  vertical preset seeded BEFORE scrape (plumbing/HVAC/cleaning/PW/landscape/electrical)

Tests 1-4 characterize EXISTING behavior (expect PASS).
Tests 5-7 prove v2 contract gaps (expect FAIL).
"""
from unittest.mock import MagicMock, AsyncMock

import httpx
import pytest

TENANT_ID = "00000000-0000-0000-0000-000000000001"
ENDPOINT = f"/api/v1/onboarding/{TENANT_ID}/auto-kb"


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset slowapi limiter storage between tests (5/hour cap collides across runs)."""
    from backend.limiter import limiter
    try:
        limiter.reset()
    except Exception:
        # Memory backend may not implement reset; clear storage directly.
        try:
            limiter._storage.storage.clear()
        except Exception:
            pass
    yield

CLAUDE_RESPONSE = """===KNOWLEDGE_BASE===
# About MN Plumbing
Local plumber serving Minneapolis metro since 2005.
## Services
- Drain cleaning
- Water heater repair
- Sewer line replacement
## Hours
Mon-Fri 8am-6pm, Sat 9am-2pm
===CUSTOM_INSTRUCTIONS===
You are the MN Plumbing Assistant.
- Local plumber, Minneapolis
- Pricing: ask for free estimate
- Scheduling: collect name + phone + issue
NEVER mention AgentNexLiFy.
===FAQ_START===
Q: Do you offer emergency service?
A: Yes 24/7 for burst pipes.
C: emergency
Q: Do you service apartments?
A: Yes, we work with property managers.
C: scope
Q: What payment do you accept?
A: Cash, check, all major cards.
C: payment
Q: How fast can you come out?
A: Same-day for emergencies, 1-2 days otherwise.
C: scheduling
Q: Are you licensed?
A: Yes, MN state license PL12345.
C: credentials
Q: Do you offer free estimates?
A: Yes for jobs over $200.
C: pricing
Q: What areas do you serve?
A: Minneapolis, St. Paul, and inner-ring suburbs.
C: scope
Q: Do you guarantee your work?
A: 1-year warranty on all installs.
C: credentials
===FAQ_END===
"""


def _setup_db(mock_supabase, business_type="plumbing"):
    tenant = MagicMock()
    tenant.data = {
        "business_name": "MN Plumbing",
        "business_type": business_type,
        "city": "Minneapolis",
        "phone": "555-0100",
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = tenant
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()


def _patch_safe(monkeypatch, allow=True):
    monkeypatch.setattr("backend.services.url_validation.is_safe_url", lambda url: allow)


def _patch_crawl(monkeypatch, content="MN Plumbing. Drain cleaning. Water heater. Mon-Fri 8-6.", pages=5):
    async def _crawl(tid, url):
        return {"pages_found": pages}
    monkeypatch.setattr("backend.services.website_crawler.start_crawl", _crawl)
    monkeypatch.setattr("backend.services.website_crawler.get_crawled_content", lambda tid: content)


def _patch_fallback_fail(monkeypatch):
    class _Fail:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def get(self, *a, **kw):
            raise httpx.ConnectError("blocked in test")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Fail())


def _patch_claude(monkeypatch, capture=None):
    fake = MagicMock()
    fake.text = CLAUDE_RESPONSE

    async def _call(**kw):
        if capture is not None:
            capture.update(kw)
        return fake

    monkeypatch.setattr("backend.routers.onboarding.call_claude_messages", _call)


# --- characterization tests (existing behavior, should PASS) ----------

def test_auto_kb_ssrf_blocks_localhost(client, auth_headers, mock_supabase):
    r = client.post(ENDPOINT, headers=auth_headers, json={"url": "http://localhost:8080/admin"})
    assert r.status_code == 400, f"expected 400 SSRF block, got {r.status_code}: {r.text}"


def test_auto_kb_ssrf_blocks_aws_metadata(client, auth_headers, mock_supabase):
    r = client.post(ENDPOINT, headers=auth_headers, json={"url": "http://169.254.169.254/latest/meta-data/"})
    assert r.status_code == 400


def test_auto_kb_422_on_no_extracted_content_and_no_preset(client, auth_headers, mock_supabase, monkeypatch):
    """422 still fires when scrape empty AND business_type has no vertical preset."""
    _setup_db(mock_supabase, business_type="other")
    _patch_safe(monkeypatch)
    _patch_crawl(monkeypatch, content="", pages=0)
    _patch_fallback_fail(monkeypatch)

    r = client.post(ENDPOINT, headers=auth_headers, json={"url": "http://example.com"})
    assert r.status_code == 422


def test_auto_kb_returns_kb_and_faqs_on_success(client, auth_headers, mock_supabase, monkeypatch):
    _setup_db(mock_supabase)
    _patch_safe(monkeypatch)
    _patch_crawl(monkeypatch)
    _patch_claude(monkeypatch)

    r = client.post(ENDPOINT, headers=auth_headers, json={"url": "http://mnplumbing.com"})
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert "knowledge_base" in body and len(body["knowledge_base"]) > 50
    assert "custom_instructions" in body
    assert "faqs" in body and len(body["faqs"]) >= 5
    assert body["pages_crawled"] >= 1


# --- v2 contract tests (expect FAIL until v2 ships) -------------------

def test_auto_kb_v2_returns_structured_services(client, auth_headers, mock_supabase, monkeypatch):
    """v2 GAP: wizard needs response.services as list[str] for pre-fill."""
    _setup_db(mock_supabase)
    _patch_safe(monkeypatch)
    _patch_crawl(monkeypatch)
    _patch_claude(monkeypatch)

    r = client.post(ENDPOINT, headers=auth_headers, json={"url": "http://mnplumbing.com"})
    body = r.json()
    assert "services" in body, (
        f"v2: response must include 'services' list. got keys: {list(body.keys())}"
    )
    assert isinstance(body["services"], list)
    assert len(body["services"]) >= 1


def test_auto_kb_v2_returns_structured_hours(client, auth_headers, mock_supabase, monkeypatch):
    """v2 GAP: wizard needs response.hours as dict[day, str] for visual grid."""
    _setup_db(mock_supabase)
    _patch_safe(monkeypatch)
    _patch_crawl(monkeypatch)
    _patch_claude(monkeypatch)

    r = client.post(ENDPOINT, headers=auth_headers, json={"url": "http://mnplumbing.com"})
    body = r.json()
    assert "hours" in body, (
        f"v2: response must include 'hours' dict. got keys: {list(body.keys())}"
    )
    assert isinstance(body["hours"], dict)
    expected_days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    actual_keys = {k.lower()[:3] for k in body["hours"].keys()}
    assert expected_days.issubset(actual_keys), (
        f"v2: hours must have all 7 day keys. got: {sorted(body['hours'].keys())}"
    )


def test_auto_kb_v2_vertical_preset_seeds_when_scrape_empty(
    client, auth_headers, mock_supabase, monkeypatch
):
    """v2 GAP: plumbing tenant gets preset services even if scrape blank.

    Wizard should never start empty for known verticals.
    Currently endpoint returns 422 on empty scrape; v2 should fall back to preset.
    """
    _setup_db(mock_supabase, business_type="plumbing")
    _patch_safe(monkeypatch)
    _patch_crawl(monkeypatch, content="", pages=0)
    _patch_fallback_fail(monkeypatch)

    r = client.post(ENDPOINT, headers=auth_headers, json={"url": "http://mnplumbing.com"})
    assert r.status_code == 200, (
        f"v2: empty scrape + plumbing preset must seed services and return 200. "
        f"got {r.status_code}: {r.text[:200]}"
    )
    body = r.json()
    assert "services" in body and len(body["services"]) >= 3
    services_lower = " ".join(body["services"]).lower()
    assert any(kw in services_lower for kw in ("drain", "water heater", "leak", "pipe")), (
        f"v2: plumbing preset must include common services. got: {body['services']}"
    )
