"""Tenant knowledge + vertical guidance feed for the Agent OS engine.

Fills the long-stubbed ``SharedContext.kb`` with the business's actual
knowledge, three layers deep, all shaped as the engine's
``KbEntry {topic, answer}`` so the vendored engine needs zero changes:

1. **Vertical guidance** — curated per-industry operating notes (terminology,
   typical jobs, what customers care about, tone). This is the "vertical
   pack" delivered through context instead of per-agent prompt forks.
2. **Tenant FAQs** — ``faq_entries`` (seeded per industry at onboarding via
   ``industry_faqs.seed_industry_faqs`` and curated by the owner since).
3. **Website text** — the crawled ``website_content.extracted_text`` summary,
   when a successful crawl exists.

The knowledge-graph + semantic memory entries (``os_graph_memory``) are
appended by the caller; this module is the *static business truth* half.
Every query is client_id-scoped; failures return [] — context enrichment
never breaks a turn.
"""

import logging

from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_FAQ_CAP = 15
_FAQ_ANSWER_CAP = 600
_WEBSITE_TEXT_CAP = 1200

# Per-industry operating guidance. Keys match the business_type vocabulary
# used by industry_faqs.resolve_business_profile_key / onboarding presets.
# Three to four entries per vertical: enough to give the departments the
# trade's voice without bloating every turn's context.
VERTICAL_GUIDANCE: dict[str, list[dict]] = {
    "auto_repair": [
        {
            "topic": "industry: how this shop talks",
            "answer": (
                "Auto repair customers care about: is my car safe, what does it "
                "cost, when do I get it back. Quote labor and parts separately "
                "when known. Use plain terms (brake pads, not friction material). "
                "Always offer a pickup time window, not a vague 'later this week'."
            ),
        },
        {
            "topic": "industry: common jobs",
            "answer": (
                "Oil change, brake pads/rotors, tire rotation and mounting, "
                "battery, diagnostics (check-engine), AC recharge, alignment, "
                "state inspection. Diagnostics usually carries its own fee that "
                "may be credited toward the repair."
            ),
        },
        {
            "topic": "industry: follow-up etiquette",
            "answer": (
                "Quotes go stale fast — follow up within 2-3 days. Reference "
                "the vehicle (year/make/model) in every message. Seasonal hooks "
                "work: AC before summer, battery and tires before winter."
            ),
        },
    ],
    "home_services": [
        {
            "topic": "industry: how contractors talk",
            "answer": (
                "Homeowners want a clear scope, a firm price or honest range, "
                "and to know who shows up and when. Lead with the estimate "
                "process. Mention licensing/insurance when relevant. Photos "
                "from the customer speed up every quote."
            ),
        },
        {
            "topic": "industry: common jobs",
            "answer": (
                "Repairs vs installs vs maintenance plans. Emergency calls "
                "(burst pipe, no heat/AC) get same-day language and after-hours "
                "rates. Estimates are usually free; diagnostic visits may not be."
            ),
        },
        {
            "topic": "industry: follow-up etiquette",
            "answer": (
                "Bid follow-up at 3 days and 7 days, then monthly. Weather "
                "events are legitimate outreach moments (storms -> roof/gutter, "
                "cold snaps -> plumbing/HVAC)."
            ),
        },
    ],
    "salon": [
        {
            "topic": "industry: how salons talk",
            "answer": (
                "Warm and personal. Use first names. Customers book people, "
                "not slots — name the stylist/tech when confirming. Mention "
                "duration so clients plan their day. No-shows are the #1 "
                "revenue leak: confirm day-before."
            ),
        },
        {
            "topic": "industry: common services",
            "answer": (
                "Cut, color (longer; book consultation for major changes), "
                "styling, nails, waxing, facials. Color corrections need an "
                "in-person look before quoting. Deposits are normal for long "
                "appointments."
            ),
        },
        {
            "topic": "industry: rebooking etiquette",
            "answer": (
                "Rebook at checkout cadence: cuts 4-6 weeks, color 6-8 weeks, "
                "nails 2-3 weeks. A lapsed-client nudge at 2x their usual "
                "cadence reads as caring, not pushy."
            ),
        },
    ],
    "dental": [
        {
            "topic": "industry: how dental offices talk",
            "answer": (
                "Calm, reassuring, never alarmist. New patients ask about "
                "insurance first — answer plainly what's accepted and what "
                "out-of-pocket looks like. Emergencies (pain, broken tooth) "
                "get same-day language and a phone number."
            ),
        },
        {
            "topic": "industry: common services",
            "answer": (
                "Cleanings/exams (the recall engine — every 6 months), "
                "fillings, crowns, whitening, Invisalign consults. Treatment "
                "plans are quoted after exam, never sight-unseen."
            ),
        },
        {
            "topic": "industry: privacy",
            "answer": (
                "Health information is sensitive. Keep messages to scheduling "
                "and logistics; clinical details belong in the office, not in "
                "SMS or email."
            ),
        },
    ],
    "realestate": [
        {
            "topic": "industry: how agents talk",
            "answer": (
                "Speed wins listings — respond to every inquiry the same hour. "
                "Buyers want photos, price, and a showing time; sellers want a "
                "valuation conversation. Always offer two concrete showing slots."
            ),
        },
        {
            "topic": "industry: follow-up etiquette",
            "answer": (
                "Nurture is long-cycle: monthly market updates beat weekly "
                "pestering. Anniversary and rate-drop touches reopen old leads."
            ),
        },
    ],
    "_default": [
        {
            "topic": "industry: small-business basics",
            "answer": (
                "Reply fast, confirm specifics (who/what/when/price), and end "
                "every customer message with one clear next step. Short beats "
                "thorough in SMS; email can carry detail."
            ),
        },
    ],
}

# business_type values that map onto a guidance pack.
_TYPE_ALIASES = {
    "auto_repair": "auto_repair",
    "auto_shop": "auto_repair",
    "automotive": "auto_repair",
    "plumbing": "home_services",
    "hvac": "home_services",
    "contractor": "home_services",
    "contractors": "home_services",
    "general_contractor": "home_services",
    "home_services": "home_services",
    "roofing": "home_services",
    "landscaping": "home_services",
    "electrical": "home_services",
    "salon": "salon",
    "spa": "salon",
    "barbershop": "salon",
    "nails": "salon",
    "dental": "dental",
    "dentist": "dental",
    "orthodontics": "dental",
    "chiropractic": "dental",
    "real_estate": "realestate",
    "realestate": "realestate",
}


def vertical_guidance(business_type: str | None) -> list[dict]:
    key = _TYPE_ALIASES.get((business_type or "").strip().lower(), "_default")
    return list(VERTICAL_GUIDANCE.get(key, VERTICAL_GUIDANCE["_default"]))


def tenant_kb_entries(db, client_id: str, business_type: str | None) -> list[dict]:
    """Static business knowledge as KbEntry rows. [] on any failure."""
    entries: list[dict] = vertical_guidance(business_type)

    faq_count = 0
    reads_ok = True
    try:
        faqs = (
            tenant_table(db, "faq_entries", client_id)
            .select("question, answer")
            .limit(_FAQ_CAP)
            .execute()
        ).data or []
        faq_count = len(faqs)
        entries.extend(
            {"topic": f["question"][:160], "answer": (f.get("answer") or "")[:_FAQ_ANSWER_CAP]}
            for f in faqs
            if f.get("question") and f.get("answer")
        )
    except Exception:
        reads_ok = False
        logger.warning("os_kb_feed: faq read failed", exc_info=True)

    has_website_text = False
    try:
        sites = (
            tenant_table(db, "website_content", client_id)
            .select("url, extracted_text, crawl_status")
            .eq("crawl_status", "completed")
            .order("crawled_at", desc=True)
            .limit(1)
            .execute()
        ).data or []
        if sites and (sites[0].get("extracted_text") or "").strip():
            has_website_text = True
            entries.append(
                {
                    "topic": f"website: {sites[0].get('url', '')}"[:160],
                    "answer": sites[0]["extracted_text"][:_WEBSITE_TEXT_CAP],
                }
            )
    except Exception:
        reads_ok = False
        logger.warning("os_kb_feed: website content read failed", exc_info=True)

    # Only diagnose gaps when the reads above actually succeeded — a DB blip
    # must not masquerade as "the business has no knowledge".
    if reads_ok:
        gap_entry = _knowledge_gap_entry(db, client_id, faq_count, has_website_text)
        if gap_entry:
            entries.append(gap_entry)

    return entries


def _knowledge_gap_entry(
    db, client_id: str, faq_count: int, has_website_text: bool
) -> dict | None:
    """Self-healing nudge for thin knowledge (express-setup path).

    Express signup promises "we teach your AI staff automatically" — when the
    crawl came back empty or basics are missing, the staff should close the
    gaps conversationally instead of answering badly. Returns a guidance
    entry listing what to ask the owner for, or None when knowledge is fine.
    """
    gaps: list[str] = []
    if not has_website_text and faq_count < 3:
        gaps.append("what the business does and which services it offers")

    try:
        tenant = (
            db.table("tenants")
            .select("city, phone, business_services")
            .eq("id", client_id)
            .limit(1)
            .execute()
        ).data
        t = tenant[0] if tenant else {}
        if not (t.get("business_services") or []):
            gaps.append("the list of services offered (with rough prices if possible)")
        if not (t.get("city") or "").strip():
            gaps.append("which city/area the business serves")
        if not (t.get("phone") or "").strip():
            gaps.append("the business phone number")
        hours = (
            db.table("business_hours")
            .select("id")
            .eq("tenant_id", client_id)
            .limit(1)
            .execute()
        ).data
        if not hours:
            gaps.append("the business hours")
    except Exception:
        # Can't verify — claim nothing rather than fabricate gaps.
        logger.warning("os_kb_feed: gap detection read failed", exc_info=True)
        return None

    if not gaps:
        return None
    gap_list = "; ".join(dict.fromkeys(gaps))
    return {
        "topic": "setup gaps — gather these from the owner",
        "answer": (
            "Your knowledge about this business is incomplete. Still missing: "
            f"{gap_list}. When the owner chats with you, weave ONE of these "
            "questions naturally into your reply (never interrogate with a "
            "list) and note the answer so it sticks. Until you know a fact, "
            "say so plainly instead of guessing."
        ),
    }
