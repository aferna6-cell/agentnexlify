"""Orchestrator — routes an owner's natural-language ask to one worker agent.

Implements the seven §11 routing rules from the agent library:

1. Confidence floor — top match < 0.5 → generalist + wishlist capture.
2. Ambiguity gap — top two within 0.1 → ask the owner which one.
3. Owner override — every decision is visible and re-routable (:meth:`override`).
4. Channel inference — "text" → SMS, "email" → email, "post" → post.
5. Specialty preference — a dollar amount + "quote" routes to Quote Follow-up
   over the generic Lead Nurture.
6. Sensitive routing — complaint language short-circuits to Complaint Handler.
7. Bucket awareness — "what marketing agents do you have?" lists a bucket.

Routing is deterministic and keyword-driven (the production classifier runs on
Haiku; this is the offline-safe equivalent). Every decision is appended to
:attr:`Orchestrator.log` so the input → agent → confidence → accepted/changed
trail accumulates from day one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent_os.context import SharedContext
from agent_os.errors import RegistryError
from agent_os.registry import REGISTRY, AgentRegistry
from agent_os.result import AgentResult, OwnerAsk
from agent_os.schema import Bucket, Channel
from agent_os.wishlist import Wishlist

# Words that carry no routing signal — stripped before token overlap scoring.
_STOPWORDS = frozenset(
    {
        "a", "an", "the", "to", "for", "of", "my", "me", "can", "you", "please",
        "i", "is", "it", "this", "that", "and", "or", "on", "in", "with", "want",
        "need", "get", "send", "write", "make", "do", "your", "our", "us", "be",
        "would", "could", "should", "draft", "up", "new", "out", "about", "some",
    }
)

_COMPLAINT_TERMS = (
    "complaint", "complain", "angry", "upset", "unhappy", "furious",
    "disappointed", "refund", "frustrated", "terrible", "awful", "horrible",
    "worst", "unacceptable", "ruined", "not happy", "never coming back",
    "fed up", "pissed", "livid", "mad about",
)

# Listing intent phrases that turn an ask into a bucket-discovery query (rule 7).
_LISTING_PHRASES = (
    "what agents", "which agents", "list agents", "list your agents",
    "what can you do", "what do you do", "what can you help",
    "what do you have", "what's in", "what is in", "show me your agents",
    "what kinds of", "what types of", "what else can you",
)

# Bucket words → bucket. Only consulted once a listing phrase is present, so
# real asks like "book an appointment" never get mistaken for a bucket query.
_BUCKET_WORDS: tuple[tuple[str, Bucket], ...] = (
    ("customer service", Bucket.customer_service),
    ("support", Bucket.customer_service),
    ("marketing", Bucket.marketing),
    ("finance", Bucket.finance),
    ("financial", Bucket.finance),
    ("money", Bucket.finance),
    ("sales", Bucket.sales),
    ("scheduling", Bucket.scheduling_ops),
    ("appointment", Bucket.scheduling_ops),
    ("booking", Bucket.scheduling_ops),
    ("reputation", Bucket.reputation),
    ("review", Bucket.reputation),
    ("reporting", Bucket.reporting),
    ("report", Bucket.reporting),
)

_AMOUNT_RE = re.compile(r"\$\s?\d|\b\d[\d,]*\s*(?:dollars|usd|bucks)\b")
_WORD_RE = re.compile(r"[a-z']+")


@dataclass
class RoutingDecision:
    """The visible outcome of routing one ask.

    Exactly one of these is true for a dispatchable decision: ``agent_id`` is
    set. When ``needs_owner_choice`` or ``is_bucket_query`` is set, ``agent_id``
    is ``None`` and there is nothing to run yet.
    """

    ask: OwnerAsk
    agent_id: str | None
    confidence: float
    reason: str
    scores: dict[str, float] = field(default_factory=dict)
    runner_up_id: str | None = None
    runner_up_confidence: float = 0.0
    needs_owner_choice: bool = False
    choice: tuple[str, str] | None = None
    choice_prompt: str | None = None
    channel_override: Channel | None = None
    is_bucket_query: bool = False
    bucket_listing: str | None = None
    used_specialty_rule: bool = False
    short_circuited: bool = False
    owner_overrode: bool = False

    @property
    def is_generalist(self) -> bool:
        return self.agent_id == "generalist"

    @property
    def dispatchable(self) -> bool:
        return self.agent_id is not None


class Orchestrator:
    CONFIDENCE_FLOOR = 0.5
    AMBIGUITY_GAP = 0.1

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        wishlist: Wishlist | None = None,
    ) -> None:
        self.registry = registry or REGISTRY
        self.wishlist = wishlist or Wishlist()
        self.log: list[RoutingDecision] = []

    # ----- routing -----
    def route(self, ask: OwnerAsk | str) -> RoutingDecision:
        if isinstance(ask, str):
            ask = OwnerAsk(text=ask)
        low = ask.text.lower()
        ask_tokens = {t for t in _WORD_RE.findall(low) if t not in _STOPWORDS}

        # Rule 4 — channel inference. Owner's explicit request always wins.
        channel_override = _infer_channel(low)
        if channel_override is not None and ask.requested_channel is None:
            ask.requested_channel = channel_override

        # Rule 7 — bucket awareness (before scoring; it's a meta-question).
        bucket = _bucket_query(low)
        if bucket is not None:
            return self._record(
                RoutingDecision(
                    ask=ask,
                    agent_id=None,
                    confidence=1.0,
                    reason="bucket discovery — listing agents",
                    is_bucket_query=True,
                    bucket_listing=self._list_bucket(bucket),
                    channel_override=channel_override,
                )
            )

        # Rule 6 — complaint short-circuit.
        if _is_complaint(low) and self.registry.has("complaint_handler"):
            return self._record(
                RoutingDecision(
                    ask=ask,
                    agent_id="complaint_handler",
                    confidence=0.95,
                    reason="complaint language detected — routed to Complaint Handler",
                    short_circuited=True,
                    channel_override=channel_override,
                )
            )

        # Score every specialist (the generalist is the fallback, never scored).
        scores: dict[str, float] = {}
        for spec in self.registry.specs():
            if spec.agent_id == "generalist":
                continue
            scores[spec.agent_id] = _score(spec, low, ask_tokens)

        # Rule 5 — specialty preference: amount + "quote" → Quote Follow-up.
        used_specialty = False
        if (
            "quote" in low
            and _AMOUNT_RE.search(low)
            and "quote_follow_up" in scores
        ):
            scores["quote_follow_up"] = max(scores["quote_follow_up"], 0.85)
            used_specialty = True

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top_id, top_score = ranked[0] if ranked else (None, 0.0)
        run_id, run_score = ranked[1] if len(ranked) > 1 else (None, 0.0)

        # Rule 1 — confidence floor → generalist + wishlist capture.
        if top_score < self.CONFIDENCE_FLOOR:
            self.wishlist.capture(
                ask.text, closest_agent_id=top_id, closest_score=top_score
            )
            fallback_id = "generalist" if self.registry.has("generalist") else None
            near = f"closest was {top_id} ({top_score:.2f})" if top_id else "no near match"
            return self._record(
                RoutingDecision(
                    ask=ask,
                    agent_id=fallback_id,
                    confidence=top_score,
                    reason=f"no specialist cleared 0.5 ({near}) — routed to generalist + captured wishlist",
                    scores=scores,
                    runner_up_id=top_id,
                    runner_up_confidence=top_score,
                    channel_override=channel_override,
                )
            )

        # Rule 2 — ambiguity gap. Specialty rule already disambiguated, so skip
        # the owner prompt when it fired.
        if (
            not used_specialty
            and run_id is not None
            and (top_score - run_score) < self.AMBIGUITY_GAP
        ):
            top_name = self.registry.get(top_id).spec.display_name
            run_name = self.registry.get(run_id).spec.display_name
            return self._record(
                RoutingDecision(
                    ask=ask,
                    agent_id=None,
                    confidence=top_score,
                    reason="top two scores within 0.1 — asking owner to choose",
                    scores=scores,
                    runner_up_id=run_id,
                    runner_up_confidence=run_score,
                    needs_owner_choice=True,
                    choice=(top_id, run_id),
                    choice_prompt=f"Sounds like {top_name} or {run_name} — which is it?",
                    channel_override=channel_override,
                )
            )

        return self._record(
            RoutingDecision(
                ask=ask,
                agent_id=top_id,
                confidence=top_score,
                reason=f"matched {top_id} (confidence {top_score:.2f})",
                scores=scores,
                runner_up_id=run_id,
                runner_up_confidence=run_score,
                channel_override=channel_override,
                used_specialty_rule=used_specialty,
            )
        )

    # ----- dispatch -----
    def dispatch(
        self, decision: RoutingDecision, context: SharedContext
    ) -> AgentResult | None:
        """Run the chosen agent through the registry (rules re-validated there).
        Returns ``None`` when the decision has nothing to run (owner choice
        pending or a bucket listing)."""

        if decision.agent_id is None:
            return None
        return self.registry.run(decision.agent_id, decision.ask, context)

    def handle(
        self, ask: OwnerAsk | str, context: SharedContext
    ) -> tuple[RoutingDecision, AgentResult | None]:
        decision = self.route(ask)
        return decision, self.dispatch(decision, context)

    # ----- rule 3: owner override -----
    def override(self, decision: RoutingDecision, new_agent_id: str) -> RoutingDecision:
        """Re-route a visible decision to a different specialist before approval."""

        if not self.registry.has(new_agent_id):
            raise RegistryError(f"unknown agent: {new_agent_id}")
        prior = decision.agent_id or "(none)"
        return self._record(
            RoutingDecision(
                ask=decision.ask,
                agent_id=new_agent_id,
                confidence=decision.confidence,
                reason=f"owner override → {new_agent_id} (was {prior})",
                scores=decision.scores,
                channel_override=decision.channel_override,
                owner_overrode=True,
            )
        )

    # ----- bucket listing (rule 7) -----
    def list_buckets(self) -> str:
        return self._list_bucket("all")

    def _list_bucket(self, target: Bucket | str) -> str:
        buckets = self.registry.buckets()
        if target == "all":
            lines = ["Here's what I can help with, by area:", ""]
            for bucket in Bucket:
                specs = buckets.get(bucket, [])
                if not specs:
                    continue
                lines.append(f"{_bucket_label(bucket)}:")
                lines += [
                    f"  - {s.display_name}: {_first_sentence(s.purpose)}" for s in specs
                ]
                lines.append("")
            return "\n".join(lines).strip()

        specs = buckets.get(target, [])
        label = _bucket_label(target)
        if not specs:
            return f"No agents in {label} yet."
        lines = [f"{label} agents:", ""]
        lines += [f"- {s.display_name}: {_first_sentence(s.purpose)}" for s in specs]
        return "\n".join(lines).strip()

    # ----- internal -----
    def _record(self, decision: RoutingDecision) -> RoutingDecision:
        self.log.append(decision)
        return decision


# ----- module-level scoring + detectors -----
def _score(spec, low: str, ask_tokens: set[str]) -> float:
    """Confidence in [0, 1] that *spec* owns the ask.

    Keyword substring hits dominate; token overlap with the keyword vocabulary
    and the purpose breaks ties. Tuned so a clear keyword hit clears the 0.5
    floor and unrelated asks fall to the generalist.
    """

    hits = [kw for kw in spec.routing_keywords if kw and kw in low]
    score = 0.0
    if hits:
        longest = max(len(kw) for kw in hits)
        score = 0.5 + 0.12 * min(len(hits), 3) + min(longest / 60.0, 0.18)

    kw_tokens: set[str] = set()
    for kw in spec.routing_keywords:
        kw_tokens |= {t for t in _WORD_RE.findall(kw.lower()) if t not in _STOPWORDS}
    purpose_tokens = {
        t for t in _WORD_RE.findall(spec.purpose.lower()) if t not in _STOPWORDS
    }
    score += 0.07 * len(ask_tokens & kw_tokens)
    score += 0.02 * len(ask_tokens & purpose_tokens)
    return min(score, 1.0)


def _infer_channel(low: str) -> Channel | None:
    if re.search(r"\btexts?\b", low) or re.search(r"\bsms\b", low):
        return Channel.sms
    if re.search(r"\be-?mail\b", low):
        return Channel.email
    if re.search(r"\b(post|social)\b", low):
        return Channel.post
    return None


def _is_complaint(low: str) -> bool:
    return any(term in low for term in _COMPLAINT_TERMS)


_LISTING_RE = re.compile(
    r"\b(what|which|list|show)\b.*\bagents?\b|\bagents?\b.*\b(do you have|can you|are there)\b"
)


def _bucket_query(low: str) -> Bucket | str | None:
    listing = any(phrase in low for phrase in _LISTING_PHRASES) or bool(
        _LISTING_RE.search(low)
    )
    if not listing:
        return None
    for word, bucket in _BUCKET_WORDS:
        if word in low:
            return bucket
    return "all"


def _bucket_label(bucket: Bucket) -> str:
    return bucket.value.replace("_", " ").capitalize()


def _first_sentence(text: str) -> str:
    text = text.strip()
    for sep in (". ", "."):
        idx = text.find(sep)
        if idx != -1:
            return text[:idx].strip()
    return text
