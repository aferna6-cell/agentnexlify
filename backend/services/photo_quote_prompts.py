"""Per-vertical confidence constants + vision prompt builder (#38).

Photo-quote accuracy varies by trade: a plumbing leak is easier to price from a
photo than roof damage. Each vertical therefore has its own confidence floor —
below it, the quote is flagged ``needs_human`` instead of shown to the customer.
Resolved decision #7 in ``specs/photo-quote_spec.md``.

This is the mig-108 quote path (``quote_requests`` + ``tenant_pricing_rules``):
Claude vision returns a single severity + low/high price range + a confidence
score, and the caller gates on the resolved threshold. It is distinct from the
mig-171 ``quote_builder.py`` Good/Better/Best catalog path.

Pure functions only — no DB, no API calls — so the pricing/threshold logic is
unit-testable in isolation. The caller loads the ``tenant_pricing_rules`` row
and passes it in.
"""

import json
from typing import Any

# Per-vertical confidence floors. Below the floor, a quote is flagged for human
# review rather than shown to the customer.
VERTICAL_CONFIDENCE_DEFAULTS = {
    "plumbing": 0.7,
    "roofing": 0.8,
    "hvac": 0.75,
    "auto_body": 0.75,
    "landscaping": 0.7,
    "pest": 0.7,
}

# Fallback floor for a vertical with no per-vertical default and no override.
# Conservative middle of the configured range — errs toward human review.
_DEFAULT_FLOOR = 0.75


def resolve_confidence_threshold(rules_row: Any) -> float:
    """Return the confidence floor to gate ``needs_human`` on.

    Prefers the tenant's explicit ``min_confidence_threshold`` override (a real
    ``0.0`` counts — only ``None``/absent falls through), then the per-vertical
    default, then a conservative safe floor for unknown verticals.
    """
    if isinstance(rules_row, dict):
        override = rules_row.get("min_confidence_threshold")
        if override is not None:
            try:
                return float(override)
            except (TypeError, ValueError):
                pass
        industry = rules_row.get("industry")
        if industry in VERTICAL_CONFIDENCE_DEFAULTS:
            return VERTICAL_CONFIDENCE_DEFAULTS[industry]
    return _DEFAULT_FLOOR


def _pricing_json(rules_row: Any) -> str:
    """Serialize the tenant's ``rules_jsonb`` pricing map for prompt injection.

    Always valid JSON — an empty ``{}`` when there are no rules, never a crash.
    """
    pricing = {}
    if isinstance(rules_row, dict):
        candidate = rules_row.get("rules_jsonb")
        if isinstance(candidate, (dict, list)):
            pricing = candidate
    return json.dumps(pricing, indent=2)


def build_vision_prompt(rules_row: Any, industry: str) -> str:
    """Build the Claude-vision system prompt for a photo-quote assessment.

    Injects the tenant's pricing JSON, the tier-severity instructions, the
    resolved confidence floor, an optional disclaimer, and the exact JSON
    output schema the caller parses into a ``quote_requests`` row.
    """
    industry = (industry or "service").strip() or "service"
    threshold = resolve_confidence_threshold(rules_row)
    pricing_block = _pricing_json(rules_row)

    disclaimer = ""
    if isinstance(rules_row, dict):
        text = rules_row.get("disclaimer_text")
        if isinstance(text, str) and text.strip():
            disclaimer = (
                f"\nInclude this disclaimer verbatim in your summary: "
                f"{text.strip()}\n"
            )

    return (
        f"You are a photo-quote estimator for a {industry} business. A customer "
        "uploaded a photo of a job. Estimate a price RANGE grounded ONLY in the "
        "tenant pricing rules below — never invent a service or a price outside "
        "these rules. If the photo does not give you enough to price the job "
        f'with at least {threshold:.2f} confidence, set severity to '
        '"needs_human".\n\n'
        f"Tenant pricing rules (JSON):\n{pricing_block}\n"
        f"{disclaimer}\n"
        "Severity tiers:\n"
        '- "minor": small, low-cost job clearly visible in the photo.\n'
        '- "major": large or complex job, higher cost, still priceable.\n'
        '- "needs_human": the photo is ambiguous, out of scope, or your '
        f"confidence is below {threshold:.2f} — a human must quote it.\n\n"
        "Respond with ONLY a JSON object, no markdown fences, no extra text:\n"
        '{"severity": "minor"|"major"|"needs_human", '
        '"quote_low": <integer dollars>, "quote_high": <integer dollars>, '
        '"confidence": <float 0.0-1.0>, '
        '"summary": "<1-3 sentence description of what you see and the basis '
        'for the estimate>"}\n\n'
        'When severity is "needs_human", set quote_low and quote_high to 0 and '
        "explain in the summary what is missing."
    )
