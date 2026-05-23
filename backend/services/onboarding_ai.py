"""Pure helpers for onboarding AI parsing.

No DB writes, no Claude calls. Parser + hours-expansion logic used by both the
``/auto-kb`` endpoint workflow and the generate-KB workflow.
"""

import re

from pydantic import BaseModel


class AutoKbFaqEntry(BaseModel):
    question: str
    answer: str
    category: str


def expand_hours_from_text(text: str) -> dict[str, str]:
    """Best-effort: parse 'Mon-Fri 8am-6pm, Sat 9am-2pm' into a 7-day dict."""
    days_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    out: dict[str, str] = {}
    pattern = (
        r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)"
        r"(?:-(Mon|Tue|Wed|Thu|Fri|Sat|Sun))?\s*"
        r"([0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)?\s*[-–]\s*"
        r"[0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)?|closed)"
    )
    for m in re.finditer(pattern, text, re.IGNORECASE):
        start = m.group(1).title()
        end = (m.group(2) or m.group(1)).title()
        val = m.group(3).strip()
        try:
            i, j = days_order.index(start), days_order.index(end)
        except ValueError:
            continue
        for d in days_order[i : j + 1]:
            out.setdefault(d, val)
    return out


def parse_auto_kb_response(
    raw: str,
) -> tuple[str, str, list[AutoKbFaqEntry], list[str], dict[str, str]]:
    """Parse Claude's auto-KB response into (kb, instructions, faqs, services, hours)."""
    kb_match = re.search(
        r"===KNOWLEDGE_BASE===\s*(.+?)(?====CUSTOM_INSTRUCTIONS===)", raw, re.DOTALL
    )
    ci_match = re.search(
        r"===CUSTOM_INSTRUCTIONS===\s*(.+?)(?====FAQ_START===)", raw, re.DOTALL
    )
    faq_match = re.search(r"===FAQ_START===\s*(.+?)===FAQ_END===", raw, re.DOTALL)
    services_match = re.search(r"===SERVICES===\s*(.+?)(?====|$)", raw, re.DOTALL)
    hours_match = re.search(r"===HOURS===\s*(.+?)(?====|$)", raw, re.DOTALL)

    knowledge_base = kb_match.group(1).strip() if kb_match else raw[:2000]
    custom_instructions = ci_match.group(1).strip() if ci_match else ""
    faqs: list[AutoKbFaqEntry] = []

    if faq_match:
        faq_text = faq_match.group(1).strip()
        entries = re.split(r"\nQ: ", "\nQ: " + faq_text)
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue
            q_match = re.match(r"(.+?)(?:\nA: )(.+?)(?:\nC: )(.+)", entry, re.DOTALL)
            if q_match:
                question = q_match.group(1).strip()
                if question.startswith("Q: "):
                    question = question[3:].strip()
                faqs.append(
                    AutoKbFaqEntry(
                        question=question,
                        answer=q_match.group(2).strip(),
                        category=q_match.group(3).strip(),
                    )
                )

    services: list[str] = []
    if services_match:
        for line in services_match.group(1).strip().splitlines():
            s = line.lstrip("-* ").strip()
            if s:
                services.append(s)
    if not services:
        kb_services = re.search(
            r"##\s*Services\s*\n(.+?)(?:\n##|\Z)",
            knowledge_base,
            re.DOTALL | re.IGNORECASE,
        )
        if kb_services:
            for line in kb_services.group(1).splitlines():
                s = line.lstrip("-* ").strip()
                if s and not s.startswith("#"):
                    services.append(s)

    hours: dict[str, str] = {}
    if hours_match:
        for line in hours_match.group(1).strip().splitlines():
            if ":" in line:
                day, val = line.split(":", 1)
                day = day.strip()[:3].title()
                val = val.strip()
                if day:
                    hours[day] = val
    if not hours:
        hours = expand_hours_from_text(knowledge_base)

    return knowledge_base, custom_instructions, faqs, services, hours
