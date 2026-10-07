"""DB-backed AI usage guardrails for tenant-facing runtime calls."""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.activity import log_activity
from backend.services.llm_runtime import ClaudeCallResult

logger = logging.getLogger(__name__)

# Token baselines by plan (2026-06-15 repricing).
# free     = lapsed/no-active-subscription state.
# chatbot  = $19.99/mo — ~$4/mo Claude budget ≈ 800k tokens at blended cost.
# agent_os = $99.99/mo — ~$25/mo Claude budget ≈ 5M tokens at blended cost.
# Legacy/grandfathered plans (agent_os_gate.AGENT_OS_PLANS members) keep the
# tiered budgets from their original contracts, matching the values
# billing_reconciliation has always audited against. Until 2026-07-22 they
# were missing here and ENFORCEMENT silently fell to the chatbot default —
# a grandfathered enterprise tenant peaked at 363k tokens in May (45% of
# that $19.99 cap; ~61% at the Sonnet-5 tokenizer's 1.35x). Re-baseline
# measurement (2026-07-22, tenant_ai_usage_monthly): heaviest tenant-month
# ever is 363k total tokens, zero alerts/hard-blocks — the current tier
# values keep ample headroom and stay unchanged.
PLAN_BASELINE_TOKENS: dict[str, int] = {
    "free": 100_000,
    "chatbot": 800_000,
    "agent_os": 5_000_000,
    "agent_os_managed": 8_000_000,
    "growth": 1_000_000,
    "autopilot": 1_200_000,
    "professional": 2_000_000,
    "enterprise": 5_000_000,
}

DEFAULT_BASELINE_TOKENS = PLAN_BASELINE_TOKENS["chatbot"]
# Profit guarantee (2026-06-16): the hard cap equals the costed baseline, so a
# tenant's monthly AI spend can never exceed the budget priced into their plan
# (~$4 chatbot vs $19.99, ~$25 agent_os vs $99.99). When they hit the cap, AI
# pauses and they can buy a usage pack (1M tokens for $24.99 - set the Stripe
# price in STRIPE_PRICE_USAGE_PACK). Alert fires at 80% of the cap so they can
# top up before the cutoff.
ALERT_MULTIPLIER = 0.8
HARD_LIMIT_MULTIPLIER = 1


@dataclass(frozen=True)
class AIUsagePolicy:
    period_month: str
    alert_threshold_tokens: int
    hard_limit_tokens: int


@dataclass(frozen=True)
class AIUsageReservation:
    allowed: bool
    tenant_id: str
    period_month: str
    estimated_tokens: int
    alert_threshold_tokens: int
    hard_limit_tokens: int
    reason: str = ""


@dataclass(frozen=True)
class AIUsageRecord:
    total_tokens: int
    alert_triggered: bool
    hard_limit_reached: bool


@dataclass(frozen=True)
class AIUsageAccountingDebt:
    """Billable usage that could not be proved as an ``AIUsageRecord``.

    ``reason="record_rpc_failed"`` means the record RPC itself raised, so
    the reservation stays held. ``reason="record_response_unproved"`` means
    the RPC returned but its payload could not be coerced into proved
    totals; nothing is invented and callers must not release.
    ``alert_triggered`` stays false so existing callers that read it
    (widget chat) do not treat either outcome as a threshold crossing or
    raise into a post-success release.
    """

    tenant_id: str
    period_month: str
    estimated_tokens: int
    operation: str
    session_id: str
    model: str
    reason: str = "record_rpc_failed"
    alert_triggered: bool = False


def current_period_month() -> str:
    now = datetime.now(timezone.utc)
    return date(now.year, now.month, 1).isoformat()


def _coerce_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            return None
        return parsed if parsed > 0 else None
    return None


def _sum_usage_packs(tenant_id: str, period_month: str) -> int:
    """Return the total bonus tokens from purchased usage packs for this period.

    Fails open (returns 0) — a DB error must never block an AI call.
    """
    try:
        result = get_service_supabase().table("tenant_usage_packs").select(
            "tokens"
        ).eq("tenant_id", tenant_id).eq("period", period_month).execute()
        rows = result.data or []
        return sum(int(r.get("tokens") or 0) for r in rows)
    except Exception:
        logger.warning(
            "Failed to sum usage packs for tenant=%s period=%s; defaulting to 0",
            tenant_id,
            period_month,
            exc_info=True,
        )
        return 0


def resolve_ai_usage_policy(tenant: dict[str, Any]) -> AIUsagePolicy:
    """Resolve plan-derived usage caps, honoring tenant-level overrides and purchased packs."""
    plan = str(tenant.get("plan") or "free").lower()
    baseline = PLAN_BASELINE_TOKENS.get(plan, DEFAULT_BASELINE_TOKENS)
    default_alert = int(baseline * ALERT_MULTIPLIER)
    default_hard = int(baseline * HARD_LIMIT_MULTIPLIER)

    alert = _coerce_positive_int(tenant.get("ai_monthly_token_alert_threshold"))
    hard = _coerce_positive_int(tenant.get("ai_monthly_token_hard_limit"))
    alert_threshold = alert or default_alert
    hard_limit = hard or default_hard

    # Add purchased usage-pack tokens to the effective hard limit.
    # The RPC receives the Python-computed limit, so packs are pure-Python.
    tenant_id = tenant.get("id")
    period_month = current_period_month()
    if tenant_id:
        pack_bonus = _sum_usage_packs(str(tenant_id), period_month)
        hard_limit += pack_bonus
        alert_threshold += pack_bonus

    if hard_limit < alert_threshold:
        logger.warning(
            "AI usage policy had hard limit below alert threshold; tenant=%s alert=%s hard=%s",
            tenant.get("id"),
            alert_threshold,
            hard_limit,
        )
        hard_limit = alert_threshold

    return AIUsagePolicy(
        period_month=period_month,
        alert_threshold_tokens=alert_threshold,
        hard_limit_tokens=hard_limit,
    )


def estimate_widget_chat_tokens(
    *,
    system_prompt: str,
    messages: list[dict[str, str]],
    max_tokens: int,
) -> int:
    """Conservative pre-call estimate used for quota reservation."""
    content_chars = len(system_prompt or "")
    content_chars += sum(len(msg.get("content") or "") for msg in messages)
    estimated_input_tokens = max(1, content_chars // 4)
    return max(500, estimated_input_tokens + max_tokens)


def _rpc_bool(data: Any) -> bool:
    if isinstance(data, bool):
        return data
    if isinstance(data, str):
        return data.strip().lower() == "true"
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, bool):
            return first
        if isinstance(first, dict):
            return _rpc_bool(next(iter(first.values()), False))
    return bool(data)


def reserve_ai_tokens(
    *,
    tenant: dict[str, Any],
    estimated_tokens: int,
    operation: str,
    session_id: str,
) -> AIUsageReservation:
    tenant_id = str(tenant["id"])
    policy = resolve_ai_usage_policy(tenant)
    estimated = max(1, int(estimated_tokens))

    try:
        result = get_service_supabase().rpc(
            "reserve_ai_token_budget",
            {
                "p_tenant_id": tenant_id,
                "p_period_month": policy.period_month,
                "p_hard_limit_tokens": policy.hard_limit_tokens,
                "p_estimated_tokens": estimated,
            },
        ).execute()
        allowed = _rpc_bool(result.data)
    except Exception:
        logger.warning(
            "AI usage guard unavailable; allowing call tenant=%s op=%s",
            tenant_id,
            operation,
            exc_info=True,
        )
        return AIUsageReservation(
            allowed=True,
            tenant_id=tenant_id,
            period_month=policy.period_month,
            estimated_tokens=estimated,
            alert_threshold_tokens=policy.alert_threshold_tokens,
            hard_limit_tokens=policy.hard_limit_tokens,
            reason="guard_unavailable",
        )

    if not allowed:
        logger.warning(
            "AI usage hard limit blocked tenant=%s op=%s estimate=%s hard=%s",
            tenant_id,
            operation,
            estimated,
            policy.hard_limit_tokens,
        )
        log_activity(
            tenant_id=tenant_id,
            activity_type="ai_usage_blocked",
            description="AI reply blocked by monthly usage guardrail",
            metadata={
                "operation": operation,
                "session_id": session_id,
                "estimated_tokens": estimated,
                "hard_limit_tokens": policy.hard_limit_tokens,
            },
        )

    return AIUsageReservation(
        allowed=allowed,
        tenant_id=tenant_id,
        period_month=policy.period_month,
        estimated_tokens=estimated,
        alert_threshold_tokens=policy.alert_threshold_tokens,
        hard_limit_tokens=policy.hard_limit_tokens,
        reason="" if allowed else "hard_limit",
    )


def release_ai_token_reservation(reservation: AIUsageReservation) -> None:
    if not reservation.allowed or reservation.reason == "guard_unavailable":
        return
    try:
        get_service_supabase().rpc(
            "release_ai_token_reservation",
            {
                "p_tenant_id": reservation.tenant_id,
                "p_period_month": reservation.period_month,
                "p_reserved_tokens": reservation.estimated_tokens,
            },
        ).execute()
    except Exception:
        logger.warning(
            "Failed to release AI token reservation tenant=%s period=%s",
            reservation.tenant_id,
            reservation.period_month,
            exc_info=True,
        )


def _usage_value(value: int | None) -> int:
    return value if isinstance(value, int) and value > 0 else 0


def _emit_accounting_diagnostic(message: str, *args: object) -> None:
    """Best-effort log. A handler failure must not escape or release spend."""
    try:
        logger.warning(message, *args)
    except Exception:
        return


def _accounting_debt(
    *,
    reservation: AIUsageReservation,
    operation: str,
    session_id: str,
    model: str,
    reason: str,
    exc: Exception,
) -> AIUsageAccountingDebt:
    """Return debt even when the diagnostic log fails.

    The line omits caller-controlled session ids, response values, and
    exception text so a newline or address cannot forge a second record.
    """
    _emit_accounting_diagnostic(
        "accounting_debt tenant=%s period=%s op=%s model=%s reserved_tokens=%s reason=%s error_type=%s",
        reservation.tenant_id,
        reservation.period_month,
        operation,
        model,
        reservation.estimated_tokens,
        reason,
        type(exc).__name__,
    )
    return AIUsageAccountingDebt(
        tenant_id=reservation.tenant_id,
        period_month=reservation.period_month,
        estimated_tokens=reservation.estimated_tokens,
        operation=operation,
        session_id=session_id,
        model=model,
        reason=reason,
    )


def _usage_record_from_payload(data: Any) -> AIUsageRecord:
    """Prove a ``record_ai_token_usage`` payload or raise without quoting it.

    The SQL function returns one jsonb object: a nonnegative integer
    ``total_tokens`` plus boolean ``alert_triggered`` and
    ``hard_limit_reached``. A one-element list of that object is the only
    wrapper accepted. Missing fields, extra rows, non-dicts, bools, floats,
    negatives, and numeric strings are not proved and must not be coerced.
    """
    if isinstance(data, list):
        if len(data) != 1 or not isinstance(data[0], dict):
            raise TypeError
        payload = data[0]
    elif isinstance(data, dict):
        payload = data
    else:
        raise TypeError

    if (
        "total_tokens" not in payload
        or "alert_triggered" not in payload
        or "hard_limit_reached" not in payload
    ):
        raise TypeError
    total = payload["total_tokens"]
    alert = payload["alert_triggered"]
    hard = payload["hard_limit_reached"]
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise TypeError
    if not isinstance(alert, bool) or not isinstance(hard, bool):
        raise TypeError
    return AIUsageRecord(
        total_tokens=total,
        alert_triggered=alert,
        hard_limit_reached=hard,
    )


def record_ai_usage(
    *,
    reservation: AIUsageReservation,
    result: ClaudeCallResult,
    operation: str,
    session_id: str,
    model: str,
) -> AIUsageRecord | AIUsageAccountingDebt | None:
    """Record actual tokens for a held reservation.

    Success returns ``AIUsageRecord`` only when the RPC payload is a
    supported object (or a one-element list of that object) with a
    nonnegative integer total and boolean threshold flags. A
    ``record_ai_token_usage`` RPC failure returns debt with
    ``reason="record_rpc_failed"`` and does not release. Any other returned
    shape, including missing or wrong-typed fields and ``.data`` access
    failures, returns debt with ``reason="record_response_unproved"`` and
    does not invent a total or raise. Threshold activity logging failures
    are swallowed after a proved record. Diagnostic logs are best-effort
    and omit raw session ids, so a logger failure cannot escape into a
    caller that releases. Denied and
    guard-unavailable reservations return None. Provider failures release
    through ``release_ai_token_reservation`` exactly once at the call site,
    before this function runs.
    """
    if not reservation.allowed or reservation.reason == "guard_unavailable":
        return None

    try:
        response = get_service_supabase().rpc(
            "record_ai_token_usage",
            {
                "p_tenant_id": reservation.tenant_id,
                "p_period_month": reservation.period_month,
                "p_reserved_tokens": reservation.estimated_tokens,
                "p_input_tokens": _usage_value(result.input_tokens),
                "p_output_tokens": _usage_value(result.output_tokens),
                "p_cache_creation_input_tokens": _usage_value(result.cache_creation_input_tokens),
                "p_cache_read_input_tokens": _usage_value(result.cache_read_input_tokens),
                "p_alert_threshold_tokens": reservation.alert_threshold_tokens,
                "p_hard_limit_tokens": reservation.hard_limit_tokens,
            },
        ).execute()
    except Exception as exc:
        return _accounting_debt(
            reservation=reservation,
            operation=operation,
            session_id=session_id,
            model=model,
            reason="record_rpc_failed",
            exc=exc,
        )

    try:
        record = _usage_record_from_payload(response.data)
    except Exception as exc:
        return _accounting_debt(
            reservation=reservation,
            operation=operation,
            session_id=session_id,
            model=model,
            reason="record_response_unproved",
            exc=exc,
        )

    if record.alert_triggered or record.hard_limit_reached:
        try:
            log_activity(
                tenant_id=reservation.tenant_id,
                activity_type="ai_usage_threshold",
                description="AI monthly usage crossed a guardrail threshold",
                metadata={
                    "operation": operation,
                    "session_id": session_id,
                    "model": model,
                    "total_tokens": record.total_tokens,
                    "alert_threshold_tokens": reservation.alert_threshold_tokens,
                    "hard_limit_tokens": reservation.hard_limit_tokens,
                    "alert_triggered": record.alert_triggered,
                    "hard_limit_reached": record.hard_limit_reached,
                },
            )
        except Exception as exc:
            _emit_accounting_diagnostic(
                "accounting_observability_failed tenant=%s period=%s op=%s model=%s error_type=%s",
                reservation.tenant_id,
                reservation.period_month,
                operation,
                model,
                type(exc).__name__,
            )

    return record


_TOKENS_PER_UNIT = 1_000  # 1 unit = 1000 tokens for customer-facing meter


def get_ai_usage_status(db: Any, tenant_id: str) -> dict[str, Any]:
    """Tenant-facing AI usage snapshot for the current month.

    Returns a usage METER in abstract units (1 unit = 1000 tokens) so the
    dashboard can show how close a tenant is to their monthly cap without
    exposing raw token counts or dollar figures.

    Public shape:
      limit_units      — monthly hard-limit expressed in units
      used_units       — tokens consumed this month in units (rounded)
      remaining_units  — max(0, limit_units - used_units)
      pct_used         — float 0.0–100.0

    Internal fields (dashboard telemetry, not exposed to end customers):
      period_month, alert_reached, hard_limit_reached
    """
    try:
        tenant_rows = (
            db.table("tenants")
            .select("id, plan, ai_monthly_token_alert_threshold, ai_monthly_token_hard_limit")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        ).data or []
        # Always attach the known tenant_id. resolve_ai_usage_policy only
        # sums purchased usage packs when tenant["id"] is present; omitting
        # id from the select previously dropped pack bonus on this meter.
        tenant_row = {**(tenant_rows[0] if tenant_rows else {}), "id": tenant_id}
        policy = resolve_ai_usage_policy(tenant_row)

        usage_rows = (
            db.table("tenant_ai_usage_monthly")
            .select("input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens")
            .eq("tenant_id", tenant_id)
            .eq("period_month", current_period_month())
            .limit(1)
            .execute()
        ).data or []
        row = usage_rows[0] if usage_rows else {}
        total_tokens = sum(
            int(row.get(col) or 0)
            for col in (
                "input_tokens",
                "output_tokens",
                "cache_creation_input_tokens",
                "cache_read_input_tokens",
            )
        )

        limit_units = max(1, policy.hard_limit_tokens // _TOKENS_PER_UNIT)
        used_units = round(total_tokens / _TOKENS_PER_UNIT)
        remaining_units = max(0, limit_units - used_units)
        pct_used = round(min(100.0, (used_units / limit_units) * 100.0), 2)

        return {
            # Customer-facing meter (no raw tokens / no $)
            "limit_units": limit_units,
            "used_units": used_units,
            "remaining_units": remaining_units,
            "pct_used": pct_used,
            # Internal dashboard fields
            "period_month": current_period_month(),
            "alert_reached": total_tokens >= policy.alert_threshold_tokens,
            "hard_limit_reached": total_tokens >= policy.hard_limit_tokens,
        }
    except Exception:
        logger.warning("get_ai_usage_status failed tenant=%s", tenant_id, exc_info=True)
        return {
            "limit_units": 0,
            "used_units": 0,
            "remaining_units": 0,
            "pct_used": 0.0,
            "period_month": current_period_month(),
            "alert_reached": False,
            "hard_limit_reached": False,
        }
