"""System bucket (library §10).

* ``lead_triage`` — event-based classifier for incoming widget conversations.
  Reads the conversation, classifies intent, and recommends which worker agent
  should draft a response (draft-only; the orchestrator dispatches).
* ``generalist`` — the honest catch-all. When no specialist fits and the model
  is unavailable it produces NO draft (``Service temporarily unavailable``)
  instead of a hollow one, suggests the closest specialist when there is one,
  and always captures the ask as a wishlist signal.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from agent_os.base import BaseAgent
from agent_os.context import SharedContext
from agent_os.result import AgentResult, OwnerAsk
from agent_os.schema import (
    Bucket,
    Channel,
    Example,
    PermissionScope,
    Priority,
    Status,
    TriggerType,
)
from agent_os.trace import ReasoningTrace

from ._helpers import build_spec, field_input


# How an intent label maps to a recommended worker agent.
_INTENT_ROUTES = {
    "question": "customer_question",
    "complaint": "complaint_handler",
    "booking": "booking",
    "sales_pitch": None,  # ignore vendor pitches
    "spam": None,
    "qualified_lead": "lead_nurture",
}


class LeadTriageAgent(BaseAgent):
    spec = build_spec(
        agent_id="lead_triage",
        display_name="Lead Triage",
        bucket=Bucket.system,
        status=Status.new,
        build_priority=Priority.P2,
        purpose=(
            "Classifies an incoming widget conversation by intent and recommends "
            "which worker agent should draft the response. Event-based; never "
            "messages the customer directly."
        ),
        routes_here_when=(
            "A new widget conversation arrives and needs routing (Phase 4 event)",
            "Owner asks to triage or classify recent widget chats",
        ),
        channel=Channel.internal,
        inputs=(
            field_input("contact_name", description="Who the conversation is with."),
            field_input("summary", description="Conversation summary, if provided directly."),
        ),
        shared_context_reads=("business_profile", "widget_history"),
        triggers_supported=(TriggerType.manual, TriggerType.event_based),
        permission_scope=PermissionScope(
            require_owner_approval=False,
            notes="Internal routing only. Fires other agents draft-only — never auto-sends.",
        ),
        title_format="Triage — {contact_name}",
        body_format="Internal classification + recommended route. Markdown OK.",
        reasoning_trace_steps=("Business profile", "Widget conversations", "Classified intent"),
        routing_keywords=(
            "triage",
            "classify",
            "what came in",
            "new chats",
            "route this lead",
            "incoming conversations",
        ),
        example_interactions=(
            Example(
                owner_ask="Triage the new widget conversations.",
                expected_route="lead_triage",
                expected_output_excerpt="intent",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        channel = self.channel_for(ask)

        convos = context.widget_history
        loaded = trace.record_load(
            "Widget conversations",
            convos,
            describe=lambda c: f"{len(c)} conversation(s) to classify",
        )

        if not loaded:
            result = AgentResult(
                agent_id=self.spec.agent_id,
                channel=channel,
                title="Triage — nothing to route",
                body=(
                    "No widget conversations on record, so there's nothing to "
                    "triage right now."
                ),
                trace=trace,
                requires_approval=False,
                metadata={"classified": 0},
            )
            result.add_orchestrator_message("No widget conversations to triage.")
            return result

        lines = ["Lead triage", ""]
        routed = 0
        recommendations: list[dict] = []
        for convo in convos:
            target = _INTENT_ROUTES.get(convo.intent)
            who = convo.contact_name or "Unknown contact"
            if target:
                routed += 1
                lines.append(
                    f"- {who} — intent **{convo.intent}** → route to `{target}` "
                    f"(draft only): {convo.summary}"
                )
                recommendations.append(
                    {"contact": who, "intent": convo.intent, "route": target}
                )
            else:
                lines.append(
                    f"- {who} — intent **{convo.intent}** → no action "
                    f"(not a customer to respond to): {convo.summary}"
                )
        trace.note(
            "Classified intent",
            f"{routed} of {len(convos)} conversation(s) recommend a draft",
        )
        body = "\n".join(lines).strip()

        result = AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=f"Triage — {len(convos)} conversation(s)",
            body=body,
            trace=trace,
            requires_approval=False,
            metadata={"classified": len(convos), "recommendations": recommendations},
        )
        if recommendations:
            joined = ", ".join(
                f"{r['contact']}→{r['route']}" for r in recommendations
            )
            result.add_orchestrator_message(
                f"Recommend drafting (with your approval): {joined}."
            )
        return result


class GeneralistAgent(BaseAgent):
    spec = build_spec(
        agent_id="generalist",
        display_name="Generalist",
        bucket=Bucket.system,
        status=Status.new,
        build_priority=Priority.P1,
        purpose=(
            "Catch-all for asks that no specialist owns. Suggests the closest "
            "specialist when there is one, captures the ask as a wishlist signal, "
            "and — when the model is unavailable — returns no draft rather than a "
            "hollow one."
        ),
        routes_here_when=(
            "No specialist agent matches the owner's request (routing confidence < 0.5)",
            "Owner asks something outside every worker agent's scope",
        ),
        channel=Channel.report,
        inputs=(
            field_input("topic", description="What the owner asked about."),
        ),
        permission_scope=PermissionScope(
            require_owner_approval=True,
            notes="Honest fallback. No draft when the model is down (no hollow output).",
        ),
        title_format="General response — {topic}",
        body_format="Helpful general note. Markdown OK (report). No draft if model unavailable.",
        reasoning_trace_steps=("Business profile", "Capability match", "Drafted response"),
        routing_keywords=(),  # generalist is the fallback; it owns no keywords
        example_interactions=(
            Example(
                owner_ask="Can you help me think through whether to hire a second technician?",
                expected_route="generalist",
                expected_output_excerpt="",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)

        # Honest capability match: is there a specialist we should have routed to?
        match_id, score = _closest_specialist(ask.text)
        if match_id:
            trace.note(
                "Capability match",
                f"closest specialist `{match_id}` (similarity {score:.2f})",
            )
        else:
            trace.note("Capability match", "no specialist is a close fit")

        # Model-unavailable path: no hollow draft. Surface the outage + wishlist.
        if not self.llm.available:
            result = AgentResult.no_draft(
                agent_id=self.spec.agent_id,
                channel=channel,
                reason=(
                    "Service temporarily unavailable — I can't draft a response to "
                    "this right now. I've logged your request so we can pick it up "
                    "once the model is back."
                ),
                trace=trace,
            )
            result.add_orchestrator_message(
                f"Wishlist captured: \"{ask.text[:120]}\" (no specialist agent owns this yet)."
            )
            result.metadata["wishlist"] = ask.text
            return result

        topic = ask.param("topic") or ask.text
        biz = profile.value("business_name") or "your business"
        fallback = (
            f"Here's my take on \"{topic}\" for {biz}:\n\n"
            "I don't have a specialized workflow for this yet, so treat this as a "
            "general starting point rather than a polished draft. Tell me the "
            "outcome you want and I can break it down further."
        )

        system = (
            "You are a helpful generalist assistant for a small-business owner. "
            "There is no specialized workflow for this request, so give a useful, "
            "honest, general response. Use the real business name. Never invent "
            "specifics you weren't given, and never use bracketed placeholders. "
            "Markdown is fine (report channel)."
        )
        prompt = (
            f"Business: {profile.loaded_summary() or 'unknown'}\n"
            f"Owner asked: {ask.text}\nGive a helpful general response."
        )
        body, _ = self.draft(
            trace=trace, system=system, prompt=prompt, fallback=fallback,
            step_name="Drafted response",
        )

        title = f"General response — {topic[:50]}".strip()
        result = AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=title,
            body=body,
            trace=trace,
            metadata={"wishlist": ask.text},
        )
        # Always capture the ask so the product team sees demand for new agents.
        result.add_orchestrator_message(
            f"Wishlist captured: \"{ask.text[:120]}\" — logged as demand for a future agent."
        )
        if match_id and score > 0.4:
            result.add_orchestrator_message(
                f"This looks close to the `{match_id}` agent — want me to use that instead?"
            )
        return result


def _closest_specialist(text: str) -> tuple[str | None, float]:
    """Return the closest non-generalist agent id and similarity score.

    Imported lazily to avoid a circular import (the registry imports the agent
    modules). Returns ``(None, 0.0)`` when the registry isn't populated yet.
    """

    try:
        from agent_os.registry import REGISTRY
    except Exception:  # pragma: no cover - defensive
        return None, 0.0

    low = text.lower()
    best_id: str | None = None
    best_score = 0.0
    for spec in REGISTRY.specs():
        if spec.agent_id == "generalist":
            continue
        # Compare against purpose + keywords; take the strongest signal.
        candidates = [spec.purpose, " ".join(spec.routing_keywords)]
        for kw in spec.routing_keywords:
            if kw and kw in low:
                # A direct keyword hit is a strong signal.
                candidates.append(low)
                break
        score = max(
            SequenceMatcher(None, low, c.lower()).ratio() for c in candidates if c
        )
        if score > best_score:
            best_id, best_score = spec.agent_id, score
    return best_id, best_score
