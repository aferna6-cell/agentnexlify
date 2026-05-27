"""Agent OS MVP — end-to-end loop demo + regression test.

Drives the full chat-first loop with an in-memory FakeSupabase and stubbed
LLM calls: a user message goes through the orchestrator, routes to the
``customer_question`` worker, the worker run produces an approval-gated
deliverable, and the agent posts its summary back to the thread.

Run as a narrated demo:  pytest tests/test_os_mvp_e2e.py -s
Run as a plain gate:     pytest tests/test_os_mvp_e2e.py -q
"""

import os

os.environ["TESTING"] = "1"

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from backend.services import orchestrator, os_workers, usage_meter
from backend.services.tenant_scope import tenant_table
from tests.test_agent_os import FakeSupabase

_TENANT = "tenant-mvp-demo"

_ORCH_DECISION = (
    '{"action": "delegate", '
    '"reply": "On it — drafting an answer for your customer now.", '
    '"agent_name": "customer_question", '
    '"deliverable_title": "Customer Answer", '
    '"reason": "", "memory": []}'
)

_WORKER_DRAFT = (
    "Hi there — yes, we're open this Saturday from 9am to 4pm. "
    "Walk-ins are welcome, but booking ahead guarantees your slot."
)


def _say(line: str) -> None:
    print(f"  {line}")


async def test_mvp_end_to_end_loop():
    """User message -> orchestrator -> worker run -> deliverable -> reply."""
    db = FakeSupabase()
    thread = (
        tenant_table(db, "os_threads", _TENANT)
        .insert({"title": "Customer asks about weekend hours"})
        .execute()
        .data[0]
    )
    thread_id = thread["id"]
    user_message = "A customer wants to know if we're open this Saturday."

    print("\n" + "=" * 64)
    print("  AGENT OS — MVP END-TO-END DEMO")
    print("=" * 64)
    _say(f"tenant={_TENANT}  thread={thread_id[:8]}")
    _say(f'user: "{user_message}"')

    # --- Stage 1: orchestrator classifies + routes -----------------------
    with (
        patch.object(orchestrator, "search_memory", new=AsyncMock(return_value=[])),
        patch.object(
            orchestrator,
            "call_claude_messages",
            new=AsyncMock(return_value=SimpleNamespace(text=_ORCH_DECISION)),
        ),
    ):
        decision = await orchestrator.orchestrate(db, _TENANT, user_message)

    assert decision.action == "delegate"
    assert decision.agent_name == "customer_question"
    assert decision.agent_name in os_workers.all_workers()
    _say(f"orchestrator -> action={decision.action} agent={decision.agent_name}")
    _say(f'orchestrator reply: "{decision.reply}"')

    # --- Stage 2: persist the queued run + assistant ack -----------------
    tenant_table(db, "os_messages", _TENANT).insert(
        {"thread_id": thread_id, "role": "user", "content": user_message}
    ).execute()
    run = (
        tenant_table(db, "os_agent_runs", _TENANT)
        .insert(
            {
                "thread_id": thread_id,
                "agent_name": decision.agent_name,
                "status": "queued",
                "thought_process": decision.thought_process,
            }
        )
        .execute()
        .data[0]
    )
    tenant_table(db, "os_messages", _TENANT).insert(
        {
            "thread_id": thread_id,
            "role": "assistant",
            "content": decision.reply,
            "agent_run_id": run["id"],
        }
    ).execute()
    _say(f"agent run {run['id'][:8]} created (status=queued)")

    # --- Stage 3: background worker runs the task ------------------------
    with (
        patch.object(os_workers, "get_service_supabase", new=lambda: db),
        patch(
            "backend.services.os_workers.customer_question.call_claude_messages",
            new=AsyncMock(return_value=SimpleNamespace(text=_WORKER_DRAFT)),
        ),
    ):
        await os_workers.run_worker(
            run["id"],
            _TENANT,
            thread_id,
            decision.agent_name,
            user_message,
            decision.deliverable_title or "Draft",
        )

    # --- Stage 4: verify the loop closed ---------------------------------
    final_run = (
        tenant_table(db, "os_agent_runs", _TENANT)
        .select("*")
        .eq("id", run["id"])
        .execute()
        .data[0]
    )
    assert final_run["status"] == "succeeded"
    assert final_run["deliverable_status"] == "pending_approval"
    assert final_run["deliverable"]["body"]
    assert final_run["deliverable"]["format"] == "markdown"
    assert len(final_run["thought_process"]) >= 2
    _say(
        f"worker finished -> run status={final_run['status']} "
        f"deliverable={final_run['deliverable_status']}"
    )
    for step in final_run["thought_process"]:
        _say(f"  - step {step['step']}: {step['label']}")

    messages = (
        tenant_table(db, "os_messages", _TENANT)
        .select("*")
        .eq("thread_id", thread_id)
        .order("created_at", desc=False)
        .execute()
        .data
    )
    roles = [m["role"] for m in messages]
    assert roles == ["user", "assistant", "agent"]
    agent_msg = messages[-1]
    assert agent_msg["agent_run_id"] == run["id"]
    _say(f'agent reply posted: "{agent_msg["content"]}"')

    deliverable = final_run["deliverable"]
    print("  " + "-" * 60)
    _say(f"DELIVERABLE (pending approval): {deliverable['title']}")
    _say(f"  {deliverable['body']}")
    print("  " + "-" * 60)

    usage = tenant_table(db, "os_tenant_usage", _TENANT).select("*").execute().data
    assert usage, "usage meter recorded nothing"
    _say(f"usage metered: {usage[0].get('agent_runs')} agent run(s) this cycle")
    assert not usage_meter.cap_reached(db, _TENANT)
    print("  MVP loop verified: orchestrate -> run -> deliverable -> reply")
    print("=" * 64)


async def test_mvp_no_fit_routes_to_backlog():
    """A request no worker can serve becomes a backlog row, not a failed run."""
    db = FakeSupabase()
    bad_decision = (
        '{"action": "delegate", "reply": "Looking into it.", '
        '"agent_name": "tax_filing", '
        '"deliverable_title": "Tax Return", '
        '"reason": "no worker fits", "memory": []}'
    )
    with (
        patch.object(orchestrator, "search_memory", new=AsyncMock(return_value=[])),
        patch.object(
            orchestrator,
            "call_claude_messages",
            new=AsyncMock(return_value=SimpleNamespace(text=bad_decision)),
        ),
    ):
        decision = await orchestrator.orchestrate(
            db, _TENANT, "File my quarterly taxes."
        )

    # Unknown worker -> orchestrator downgrades delegate to backlog.
    assert decision.action == "backlog"
    assert decision.agent_name is None
