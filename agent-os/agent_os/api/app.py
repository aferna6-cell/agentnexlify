"""FastAPI app for the Agent OS demo.

Endpoints (all under ``/api``):

- ``GET  /api/health``    provider + agent count
- ``GET  /api/agents``    every registered agent, grouped by bucket
- ``GET  /api/buckets``   the owner-facing bucket listing (rule 7 output)
- ``GET  /api/samples``   the demo's sample asks (quick buttons for the web UI)
- ``POST /api/route``     route one ask, dispatch it, return decision + draft
- ``GET  /api/wishlist``  asks no specialist owned (demand signal)
- ``GET  /api/log``       the routing decision log

The static web client in ``../../web`` is mounted at ``/`` when present, so
``uvicorn agent_os.api.app:app`` serves both the API and the UI on one port.

IMPORTANT: no ``from __future__ import annotations`` here — PEP 563 deferred
annotations break Pydantic body resolution (every request 422s).
"""

from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent_os.demo.sample_data import sample_asks, sample_context
from agent_os.errors import RegistryError
from agent_os.llm import default_provider
from agent_os.orchestrator import Orchestrator, RoutingDecision
from agent_os.registry import REGISTRY
from agent_os.result import AgentResult, OwnerAsk
from agent_os.schema import Bucket, Channel

# One orchestrator + one context per process. The wishlist and log accumulate
# across requests so the demo shows the trail growing.
_ORCH = Orchestrator()
_CONTEXT = sample_context()

app = FastAPI(
    title="Agent OS",
    version="0.1.0",
    description="Orchestrator + 18 worker agents for small-business automation.",
)

# Demo runs the API and a static client that may be opened from file:// or a
# different port. Permissive CORS is fine for a local demo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----- response/request models -----
class TraceStepModel(BaseModel):
    name: str
    loaded: bool
    detail: str
    summary: Optional[str] = None


class DecisionModel(BaseModel):
    ask_text: str
    agent_id: Optional[str]
    agent_display_name: Optional[str]
    confidence: float
    reason: str
    scores: dict[str, float]
    runner_up_id: Optional[str]
    runner_up_confidence: float
    needs_owner_choice: bool
    choice: Optional[list[str]]
    choice_prompt: Optional[str]
    channel_override: Optional[str]
    is_bucket_query: bool
    bucket_listing: Optional[str]
    used_specialty_rule: bool
    short_circuited: bool
    owner_overrode: bool
    is_generalist: bool
    dispatchable: bool


class ResultModel(BaseModel):
    agent_id: str
    channel: str
    title: str
    body: str
    has_draft: bool
    requires_approval: bool
    flagged: bool
    orchestrator_messages: list[str]
    trace: list[TraceStepModel]


class RouteRequest(BaseModel):
    text: str = Field(
        ..., min_length=1, description="The owner's natural-language ask."
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Params a production classifier would extract (customer name, amount, ...).",
    )
    channel: Optional[str] = Field(
        None,
        description="Explicit channel request (sms|email|post|...); overrides inference.",
    )


class RouteResponse(BaseModel):
    decision: DecisionModel
    result: Optional[ResultModel]


class AgentModel(BaseModel):
    agent_id: str
    display_name: str
    bucket: str
    channel: str
    purpose: str
    status: str
    build_priority: str
    is_customer_facing: bool
    can_use_markdown: bool


class BucketGroup(BaseModel):
    bucket: str
    label: str
    agents: list[AgentModel]


class HealthResponse(BaseModel):
    status: str
    provider: str
    provider_available: bool
    agent_count: int
    bucket_count: int


class WishlistItem(BaseModel):
    ask_text: str
    closest_agent_id: Optional[str]
    closest_score: float


# ----- serializers (dataclass -> model) -----
def _display_name(agent_id: Optional[str]) -> Optional[str]:
    if agent_id and REGISTRY.has(agent_id):
        return REGISTRY.get(agent_id).spec.display_name
    return None


def _decision_model(d: RoutingDecision) -> DecisionModel:
    return DecisionModel(
        ask_text=d.ask.text,
        agent_id=d.agent_id,
        agent_display_name=_display_name(d.agent_id),
        confidence=round(d.confidence, 4),
        reason=d.reason,
        scores={k: round(v, 4) for k, v in d.scores.items()},
        runner_up_id=d.runner_up_id,
        runner_up_confidence=round(d.runner_up_confidence, 4),
        needs_owner_choice=d.needs_owner_choice,
        choice=list(d.choice) if d.choice else None,
        choice_prompt=d.choice_prompt,
        channel_override=d.channel_override.value if d.channel_override else None,
        is_bucket_query=d.is_bucket_query,
        bucket_listing=d.bucket_listing,
        used_specialty_rule=d.used_specialty_rule,
        short_circuited=d.short_circuited,
        owner_overrode=d.owner_overrode,
        is_generalist=d.is_generalist,
        dispatchable=d.dispatchable,
    )


def _result_model(r: AgentResult) -> ResultModel:
    return ResultModel(
        agent_id=r.agent_id,
        channel=r.channel.value,
        title=r.title,
        body=r.body,
        has_draft=r.has_draft,
        requires_approval=r.requires_approval,
        flagged=r.flagged,
        orchestrator_messages=list(r.orchestrator_messages),
        trace=[TraceStepModel(**step) for step in r.trace.to_list()],
    )


def _bucket_label(bucket: Bucket) -> str:
    return bucket.value.replace("_", " ").title()


# ----- endpoints -----
@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    provider = default_provider()
    return HealthResponse(
        status="ok",
        provider=provider.name,
        provider_available=provider.available,
        agent_count=len(REGISTRY),
        bucket_count=len(REGISTRY.buckets()),
    )


@app.get("/api/agents", response_model=list[BucketGroup])
def list_agents() -> list[BucketGroup]:
    buckets = REGISTRY.buckets()
    groups: list[BucketGroup] = []
    for bucket in Bucket:
        specs = buckets.get(bucket, [])
        if not specs:
            continue
        groups.append(
            BucketGroup(
                bucket=bucket.value,
                label=_bucket_label(bucket),
                agents=[
                    AgentModel(
                        agent_id=s.agent_id,
                        display_name=s.display_name,
                        bucket=s.bucket.value,
                        channel=s.channel.value,
                        purpose=s.purpose,
                        status=s.status.value,
                        build_priority=s.build_priority.value,
                        is_customer_facing=s.is_customer_facing,
                        can_use_markdown=s.can_use_markdown,
                    )
                    for s in specs
                ],
            )
        )
    return groups


@app.get("/api/buckets")
def buckets() -> dict[str, str]:
    return {"listing": _ORCH.list_buckets()}


@app.get("/api/samples")
def samples() -> list[dict[str, Any]]:
    return [{"text": ask.text, "params": ask.params} for ask in sample_asks()]


@app.post("/api/route", response_model=RouteResponse)
def route(req: RouteRequest) -> RouteResponse:
    channel: Optional[Channel] = None
    if req.channel:
        try:
            channel = Channel(req.channel)
        except ValueError:
            raise HTTPException(
                status_code=422, detail=f"unknown channel: {req.channel}"
            )

    ask = OwnerAsk(text=req.text, params=req.params, requested_channel=channel)
    try:
        decision, result = _ORCH.handle(ask, _CONTEXT)
    except RegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return RouteResponse(
        decision=_decision_model(decision),
        result=_result_model(result) if result is not None else None,
    )


@app.get("/api/wishlist", response_model=list[WishlistItem])
def wishlist() -> list[WishlistItem]:
    return [
        WishlistItem(
            ask_text=e.ask_text,
            closest_agent_id=e.closest_agent_id,
            closest_score=round(e.closest_score, 4),
        )
        for e in _ORCH.wishlist.entries()
    ]


@app.get("/api/log", response_model=list[DecisionModel])
def log() -> list[DecisionModel]:
    return [_decision_model(d) for d in _ORCH.log]


# ----- static web client (mounted last so /api/* wins) -----
_WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if _WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_WEB_DIR), html=True), name="web")
