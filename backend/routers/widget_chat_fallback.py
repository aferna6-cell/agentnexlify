"""Second-tier managed-agent fallback for widget chat (issue #472 split).

Moved verbatim from backend/routers/widget_chat.py. When first-tier Claude
emits the FALLBACK_TO_SUPPORT_AGENT marker and the widget config opts in,
the support_agent managed agent takes over the turn; low confidence,
timeout, or errors force a human handoff instead.

Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import logging
from time import perf_counter

from backend.services.activity import log_activity

logger = logging.getLogger(__name__)


# Token the first-tier Claude emits to ask for the managed-agent fallback.
# Defined at module level so tests can patch it if needed and so the two
# call sites (prompt-builder + detector) stay in sync.
FALLBACK_MARKER = "FALLBACK_TO_SUPPORT_AGENT"

# Hard ceiling for the managed-agent fallback round-trip. support_agent's
# 50th percentile is 4.6s on the 2026-04-10 smoke but Opus-heavy cases can
# push toward 15s. 8s keeps the widget responsive — over-budget means human
# handoff, which is the same degradation the user would get if first-tier
# Claude had said HANDOFF_REQUESTED directly.
FALLBACK_TIMEOUT_SECONDS = 8.0


async def _run_support_fallback(
    *,
    assistant_text: str,
    widget: dict,
    tenant_id: str,
    session_id: str,
    customer_message: str,
) -> tuple[str, bool]:
    """Second-tier managed-agent fallback for widget chat.

    When the first-tier Claude reply contains the FALLBACK_MARKER and the
    widget config has enable_ai_fallback=True, call the support_agent
    managed agent (with an 8s timeout) and either:

    - high / medium confidence → replace assistant_text with the agent answer
    - low confidence / timeout / error → force HANDOFF_REQUESTED

    Returns (new_assistant_text, ai_fallback_fired).

    If the flag is off but the marker leaked anyway, the marker is stripped
    and no fallback call is made. If neither condition is true the input
    text and False are returned unchanged.

    Imports for asyncio / run_in_threadpool / support_agent are lazy so
    this helper stays cheap on the happy path where the marker is absent.
    """
    has_marker = FALLBACK_MARKER in assistant_text
    fallback_enabled = bool(widget.get("enable_ai_fallback"))

    if not has_marker:
        return assistant_text, False

    if not fallback_enabled:
        # Flag off but first-tier Claude leaked the marker anyway. Strip
        # it so end users never see internal control tokens.
        return assistant_text.replace(FALLBACK_MARKER, "").strip(), False

    # Strip the marker up-front. If the fallback fails we still need a
    # clean base string to attach the human-handoff prefix to.
    assistant_text = assistant_text.replace(FALLBACK_MARKER, "").strip()

    import asyncio
    from fastapi.concurrency import run_in_threadpool
    from backend.services.managed_agents_registry import (
        ManagedAgentNotConfigured,
    )
    from backend.services import support_agent as _support_agent_mod
    from backend.services import agent_sdk_client as _agent_sdk

    fallback_start = perf_counter()
    fallback_confidence: str | None = None
    fallback_escalate_reason: str | None = None
    fallback_success = False
    fallback_answer: str | None = None
    fallback_error: str | None = None
    generic_handoff_text = (
        "Let me connect you with our team so you get the right answer "
        "faster.\nHANDOFF_REQUESTED"
    )

    # --- agent-service path (preferred when AGENT_SERVICE_URL is set) ---
    # Build the support prompt once (Supabase context load) then try the
    # SDK-backed widget-support agent. Falls through to managed-agents on
    # any failure so existing behavior is fully preserved.
    _sdk_result = None
    if _agent_sdk.is_configured():
        try:
            _sdk_prompt = await asyncio.wait_for(
                run_in_threadpool(
                    _support_agent_mod.build_support_prompt,
                    tenant_id,
                    customer_message,
                    session_id,
                ),
                timeout=FALLBACK_TIMEOUT_SECONDS,
            )
            _sdk_raw = await asyncio.wait_for(
                run_in_threadpool(
                    _agent_sdk.run_agent_sync,
                    "widget-support",
                    _sdk_prompt,
                    timeout=FALLBACK_TIMEOUT_SECONDS - 1.0,
                ),
                timeout=FALLBACK_TIMEOUT_SECONDS,
            )
            if _sdk_raw and not _sdk_raw.get("is_error"):
                _sdk_result = _support_agent_mod.parse_support_reply(
                    _sdk_raw.get("result") or ""
                )
                logger.info(
                    "widget_chat: agent_sdk_fallback session=%s turns=%s cost_usd=%.4f",
                    session_id,
                    _sdk_raw.get("turns"),
                    _sdk_raw.get("cost_usd", 0),
                )
        except Exception:
            logger.warning(
                "widget_chat: agent_sdk_fallback failed session=%s — "
                "falling back to managed agents",
                session_id,
                exc_info=True,
            )

    try:
        if _sdk_result is not None:
            fallback_result = _sdk_result
        else:
            fallback_result = await asyncio.wait_for(
                run_in_threadpool(
                    _support_agent_mod.run_support_query,
                    tenant_id,
                    customer_message,
                    session_id,
                ),
                timeout=FALLBACK_TIMEOUT_SECONDS,
            )
        fallback_confidence = fallback_result.get("confidence", "low")
        fallback_escalate_reason = fallback_result.get("escalate_reason")
        fallback_answer = fallback_result.get("answer")

        if fallback_confidence in ("high", "medium") and fallback_answer:
            assistant_text = fallback_answer.strip()
            fallback_success = True
            logger.info(
                "widget_chat: managed_agent_fallback SUCCESS session=%s "
                "confidence=%s",
                session_id,
                fallback_confidence,
            )
        else:
            # Low confidence — force human handoff. Attach the agent's
            # best-effort answer (if any) so the customer sees something
            # useful while the team is paged.
            handoff_prefix = (
                fallback_answer.strip()
                if isinstance(fallback_answer, str) and fallback_answer.strip()
                else (
                    "I don't have a confident answer for that — let me "
                    "connect you with our team right away."
                )
            )
            assistant_text = f"{handoff_prefix}\nHANDOFF_REQUESTED"
            logger.info(
                "widget_chat: managed_agent_fallback LOW_CONFIDENCE "
                "session=%s reason=%s",
                session_id,
                fallback_escalate_reason,
            )
    except asyncio.TimeoutError:
        fallback_error = "timeout"
        assistant_text = generic_handoff_text
        logger.warning(
            "widget_chat: managed_agent_fallback TIMEOUT session=%s — "
            "forcing human handoff",
            session_id,
        )
    except ManagedAgentNotConfigured as exc:
        fallback_error = f"not_configured: {exc}"
        assistant_text = generic_handoff_text
        logger.warning(
            "widget_chat: managed_agent_fallback NOT_CONFIGURED "
            "session=%s — forcing human handoff (%s)",
            session_id,
            exc,
        )
    except Exception as exc:  # noqa: BLE001
        fallback_error = f"exception: {type(exc).__name__}"
        assistant_text = generic_handoff_text
        logger.exception(
            "widget_chat: managed_agent_fallback ERROR session=%s — "
            "forcing human handoff",
            session_id,
        )
    finally:
        fallback_duration_ms = int((perf_counter() - fallback_start) * 1000)
        try:
            log_activity(
                tenant_id=tenant_id,
                activity_type="ai_fallback_fired",
                description=("Widget chat escalated to support_agent managed agent"),
                metadata={
                    "session_id": session_id,
                    "confidence": fallback_confidence,
                    "escalate_reason": fallback_escalate_reason,
                    "duration_ms": fallback_duration_ms,
                    "success": fallback_success,
                    "error": fallback_error,
                },
            )
        except Exception:
            logger.warning(
                "widget_chat: failed to log ai_fallback_fired activity "
                "for session %s",
                session_id,
                exc_info=True,
            )

    return assistant_text, True
