#!/usr/bin/env python3
"""
source-validation/scripts/score.py

Score a raw KB source markdown file on reliability, bias, and relevance.
Deterministic heuristics only — no LLM calls.

Usage:
    python score.py <path-to-md>

Output (stdout):
    JSON scorecard

Exit codes:
    0 — always (even on reject-level score)
    1 — file not found or unreadable
"""

import json
import re
import sys
from pathlib import Path

# --- Domain lists ---

RELIABILITY_HIGH = [
    r"\.edu\b", r"\.gov\b", r"arxiv\.org", r"nature\.com", r"science\.org",
    r"pubmed\.", r"ncbi\.nlm\.nih\.gov", r"openai\.com", r"anthropic\.com",
    r"research\.google", r"deepmind\.com", r"techcrunch\.com", r"theverge\.com",
    r"arstechnica\.com", r"wired\.com", r"gartner\.com", r"forrester\.com",
    r"vercel\.com/blog", r"stripe\.com/blog", r"supabase\.com/blog",
    r"news\.ycombinator\.com",
]

RELIABILITY_LOW = [
    r"sponsored[\s_-]content", r"affiliate", r"best.*2024.*buy",
    r"seo[\s_-]farm", r"content[\s_-]farm", r"made[\s_-]for[\s_-]adsense",
    r"#sponsored", r"paid[\s_-]placement", r"advertorial",
    r"10[\s_-]best[\s_-]", r"top[\s_-]10[\s_-]",
]

LOADED_WORDS = [
    r"\bobviously\b", r"\bclearly\b", r"\bmust\b", r"\brevolutionary\b",
    r"\bgame[\s_-]changer\b", r"\bunprecedented\b", r"\bbest[\s_-]ever\b",
    r"\bincredible\b", r"\bamazing\b", r"\bperfect\b", r"\bbest-in-class\b",
    r"\bgroundbreaking\b", r"\bdisruptive\b",
]

HEDGED_WORDS = [
    r"\bmay\b", r"\bmight\b", r"\bcould\b", r"\bsuggests?\b",
    r"\bappears?\b", r"\bindicates?\b", r"\bevidence indicates?\b",
    r"\baccording to\b", r"\bour analysis\b", r"\bwe found\b",
    r"\bdata shows\b", r"\bstudies? show\b",
]

AGENTNEXLIFY_KEYWORDS = [
    r"\bwidget\b", r"\blead\b", r"\btenant\b", r"\bclient_id\b",
    r"\bconversation\b", r"\bsmall business\b", r"\bchatbot\b",
    r"\bappointment\b", r"\bautomation\b", r"\bembeddable\b",
    r"\bmulti[\s_-]tenant\b", r"\bcrm\b", r"\bsaas\b",
    r"\bai[\s_-]receptionist\b", r"\blive[\s_-]chat\b",
]


def score_reliability(text: str, source_url: str) -> tuple[int, list[str]]:
    reasons = []
    score = 6  # default

    text_lower = text.lower()
    url_lower = (source_url or "").lower()
    combined = text_lower + " " + url_lower

    for pattern in RELIABILITY_HIGH:
        if re.search(pattern, combined):
            score = 10
            reasons.append(f"high-trust domain signal: {pattern}")
            break

    for pattern in RELIABILITY_LOW:
        if re.search(pattern, text_lower):
            score = max(score - 4, 2)
            reasons.append(f"low-trust signal: {pattern}")

    if score == 6:
        reasons.append("default reliability (no strong domain signal)")

    return score, reasons


def score_bias(text: str) -> tuple[int, list[str]]:
    reasons = []
    words = text.split()
    word_count = max(len(words), 1)

    loaded_count = sum(
        len(re.findall(p, text, re.IGNORECASE)) for p in LOADED_WORDS
    )
    hedged_count = sum(
        len(re.findall(p, text, re.IGNORECASE)) for p in HEDGED_WORDS
    )

    loaded_rate = loaded_count / word_count * 1000  # per 1000 words
    hedged_rate = hedged_count / word_count * 1000

    # Low loaded_rate + reasonable hedged_rate = high score
    if loaded_rate < 1 and hedged_rate >= 2:
        score = 9
        reasons.append(f"low loaded words ({loaded_rate:.1f}/1k), good hedging ({hedged_rate:.1f}/1k)")
    elif loaded_rate < 3:
        score = 7
        reasons.append(f"moderate loaded words ({loaded_rate:.1f}/1k)")
    elif loaded_rate < 6:
        score = 5
        reasons.append(f"elevated loaded words ({loaded_rate:.1f}/1k)")
    else:
        score = 2
        reasons.append(f"high loaded word density ({loaded_rate:.1f}/1k) — likely promotional")

    return score, reasons


def score_relevance(text: str) -> tuple[int, list[str]]:
    text_lower = text.lower()
    hits = []
    for pattern in AGENTNEXLIFY_KEYWORDS:
        matches = re.findall(pattern, text_lower)
        if matches:
            hits.append(pattern.strip(r"\b"))

    hit_count = len(hits)
    if hit_count >= 6:
        score = 10
    elif hit_count >= 4:
        score = 8
    elif hit_count >= 2:
        score = 6
    elif hit_count == 1:
        score = 4
    else:
        score = 1

    reasons = [f"{hit_count} keyword hits: {', '.join(hits[:5])}"] if hits else ["no AgentNexLiFy keyword matches"]
    return score, reasons


def action_from_score(score: float) -> str:
    if score >= 8.0:
        return "auto-promote"
    elif score >= 6.0:
        return "caveat"
    elif score >= 4.0:
        return "quarantine"
    else:
        return "reject"


def extract_source_url(text: str) -> str:
    match = re.search(r"source_url:\s*['\"]?(\S+)['\"]?", text)
    return match.group(1) if match else ""


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: score.py <path-to-md>"}), file=sys.stderr)
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        print(json.dumps({"error": f"File not found: {path}"}), file=sys.stderr)
        return 1

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    source_url = extract_source_url(text)

    rel_score, rel_reasons = score_reliability(text, source_url)
    bias_score, bias_reasons = score_bias(text)
    rev_score, rev_reasons = score_relevance(text)

    composite = round(rel_score * 0.5 + bias_score * 0.3 + rev_score * 0.2, 2)
    action = action_from_score(composite)

    result = {
        "score": composite,
        "reliability": rel_score,
        "bias": bias_score,
        "relevance": rev_score,
        "action": action,
        "reasons": rel_reasons + bias_reasons + rev_reasons,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
