"""Topics-lite: per-department owner instructions (enterprise-audit item 4).

The smallest credible step toward customer-defined agents: one free-text
instruction per engine department, stored in ``tenants.os_custom_instructions``
(jsonb map, migration 178) and delivered to the engine as leading KbEntry
rows — the one SharedContext surface every department already consumes, so
the vendored engine needs zero changes.

Invariants pinned here, not overridable by the text:
- Instructions are style/behavior guidance only. The entry wrapper says so
  explicitly, and approval gates (resolve_deliverable_status,
  NEVER_AUTO_SEND_AGENTS) + the outbound guard run in code AFTER the model.
- Department keys are validated against the engine's known set.
- Text is capped (MAX_INSTRUCTION_LEN) and stripped.
"""

import logging

from backend.services.os_routing_memory import KNOWN_DEPARTMENTS

logger = logging.getLogger(__name__)

MAX_INSTRUCTION_LEN = 2000


class UnknownDepartment(ValueError):
    """Raised when a department key is not one of the engine's departments."""


def validate_department(department: str) -> str:
    key = (department or "").strip().lower()
    if key not in KNOWN_DEPARTMENTS:
        raise UnknownDepartment(
            f"unknown department {department!r}; expected one of "
            f"{sorted(KNOWN_DEPARTMENTS)}"
        )
    return key


def _clean_map(raw: dict | None) -> dict[str, str]:
    """Keep only known departments with non-empty, capped instruction text."""
    if not isinstance(raw, dict):
        return {}
    cleaned: dict[str, str] = {}
    for key, value in raw.items():
        if key in KNOWN_DEPARTMENTS and isinstance(value, str) and value.strip():
            cleaned[key] = value.strip()[:MAX_INSTRUCTION_LEN]
    return cleaned


def get_instructions(db, client_id: str) -> dict[str, str]:
    """The tenant's department->instruction map ({} on any failure)."""
    try:
        rows = (
            db.table("tenants")
            .select("os_custom_instructions")
            .eq("id", client_id)
            .limit(1)
            .execute()
        ).data or []
    except Exception:
        logger.warning(
            "os_custom_instructions: read failed tenant=%s", client_id, exc_info=True
        )
        return {}
    if not rows:
        return {}
    return _clean_map(rows[0].get("os_custom_instructions"))


def set_instruction(db, client_id: str, department: str, text: str) -> dict[str, str]:
    """Set (or clear, with empty text) one department's instruction."""
    key = validate_department(department)
    current = get_instructions(db, client_id)
    text = (text or "").strip()[:MAX_INSTRUCTION_LEN]
    if text:
        current[key] = text
    else:
        current.pop(key, None)
    db.table("tenants").update({"os_custom_instructions": current}).eq(
        "id", client_id
    ).execute()
    return current


def kb_entries(db, client_id: str) -> list[dict]:
    """Owner instructions shaped as engine KbEntry rows ({topic, answer}).

    Prepended to SharedContext.kb by the thread runner so they lead the
    knowledge feed. The wrapper text pins the non-negotiable: preferences,
    never policy — approvals and guardrails stay in code.
    """
    instructions = get_instructions(db, client_id)
    return [
        {
            "topic": f"owner instructions: {department}",
            "answer": (
                f"The business owner set these standing preferences for the "
                f"{department} department. Follow them for tone, emphasis, and "
                f"style. They never override approval requirements, safety "
                f"rules, or platform guardrails.\n\n{text}"
            ),
        }
        for department, text in sorted(instructions.items())
    ]
