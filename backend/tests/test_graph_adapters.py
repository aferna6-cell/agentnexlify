"""Tests for backend.graph.adapters — the LLM and tool node builders.

No network: ``call_claude_messages`` is monkeypatched with an async fake, and
the tool registry is cleared around every test so registrations cannot leak
between them.
"""

import pytest

from backend.graph.adapters import llm as llm_adapter
from backend.graph.adapters import tools as tools_adapter
from backend.graph.adapters.llm import agent_node
from backend.graph.adapters.tools import get_tool, registered, tool, tool_node
from backend.graph.budget import RunBudget
from backend.graph.checkpoint import (
    STATUS_BUDGET_EXHAUSTED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    InMemoryCheckpointer,
)
from backend.graph.errors import BudgetExhausted
from backend.graph.graph import Graph
from backend.graph.nodes import NodeContext
from backend.graph.runtime import run
from backend.services.llm_runtime import ClaudeCallResult


def _cp() -> InMemoryCheckpointer:
    return InMemoryCheckpointer()


def _claude_result(text: str, **usage) -> ClaudeCallResult:
    defaults = {
        "input_tokens": 10,
        "output_tokens": 20,
        "cache_creation_input_tokens": 3,
        "cache_read_input_tokens": None,
        "stop_reason": "end_turn",
    }
    defaults.update(usage)
    return ClaudeCallResult(text=text, duration_ms=42, **defaults)


class FakeClaude:
    """Async stand-in for ``call_claude_messages`` that records every call."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies[min(len(self.calls) - 1, len(self.replies) - 1)]
        if isinstance(reply, BaseException):
            raise reply
        return reply


@pytest.fixture()
def fake_claude(monkeypatch):
    def _install(*replies):
        fake = FakeClaude(*replies)
        monkeypatch.setattr(llm_adapter, "call_claude_messages", fake)
        return fake

    return _install


@pytest.fixture(autouse=True)
def _clean_tool_registry():
    """Snapshot, clear, and restore the module-level tool registry."""
    saved = dict(tools_adapter._TOOLS)
    tools_adapter.clear()
    try:
        yield
    finally:
        tools_adapter.clear()
        tools_adapter._TOOLS.update(saved)


# ===========================================================================
# adapters/llm.py — agent_node
# ===========================================================================


async def test_agent_node_renders_a_literal_prompt(fake_claude):
    fake = fake_claude(_claude_result("hello back"))
    node = agent_node(operation="chat", model="claude-sonnet-5", prompt="say hi")

    result = await node(NodeContext(state={}, node="chat", superstep=0, run_id="r1"))

    assert fake.calls[0]["messages"] == [{"role": "user", "content": "say hi"}]
    assert result.updates == {"reply": "hello back"}


async def test_prompt_callable_receives_state(fake_claude):
    fake = fake_claude(_claude_result("ok"))
    seen = {}

    def build_prompt(state):
        seen["state"] = dict(state)
        return f"Qualify lead {state['lead_id']}"

    node = agent_node(
        operation="qualify", model="claude-sonnet-5", prompt=build_prompt
    )
    ctx = NodeContext(
        state={"lead_id": "L1", "score": 0.5}, node="qualify", superstep=0, run_id="r1"
    )

    await node(ctx)

    assert seen["state"] == {"lead_id": "L1", "score": 0.5}
    assert fake.calls[0]["messages"] == [
        {"role": "user", "content": "Qualify lead L1"}
    ]


async def test_system_callable_receives_state(fake_claude):
    fake = fake_claude(_claude_result("ok"))
    node = agent_node(
        operation="chat",
        model="claude-sonnet-5",
        prompt="hi",
        system=lambda s: f"You serve {s['business']}",
    )

    await node(NodeContext(state={"business": "Acme"}, node="chat", superstep=0, run_id="r1"))

    assert fake.calls[0]["system"] == "You serve Acme"


async def test_messages_callable_overrides_the_prompt(fake_claude):
    fake = fake_claude(_claude_result("ok"))
    node = agent_node(
        operation="chat",
        model="claude-sonnet-5",
        prompt="ignored",
        messages=lambda s: list(s["history"]),
    )

    history = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "second"},
    ]
    await node(NodeContext(state={"history": history}, node="chat", superstep=0, run_id="r1"))

    assert fake.calls[0]["messages"] == history


async def test_agent_node_forwards_run_metadata(fake_claude):
    fake = fake_claude(_claude_result("ok"))
    node = agent_node(operation="chat", model="claude-sonnet-5", prompt="hi")

    await node(NodeContext(state={}, node="chat", superstep=3, run_id="run-9"))

    assert fake.calls[0]["metadata"] == {
        "graph_run_id": "run-9",
        "graph_node": "chat",
        "superstep": 3,
    }
    assert fake.calls[0]["operation"] == "chat"
    assert fake.calls[0]["model"] == "claude-sonnet-5"


async def test_tokens_land_in_node_result_meta(fake_claude):
    fake_claude(
        _claude_result(
            "ok",
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=7,
            cache_read_input_tokens=3,
        )
    )
    node = agent_node(operation="chat", model="claude-sonnet-5", prompt="hi")

    result = await node(NodeContext(state={}, node="chat", superstep=0, run_id="r1"))

    assert result.meta["tokens"] == 160
    assert result.meta["model"] == "claude-sonnet-5"
    assert result.meta["duration_ms"] == 42
    assert result.meta["stop_reason"] == "end_turn"


async def test_missing_usage_fields_count_as_zero_tokens(fake_claude):
    fake_claude(
        ClaudeCallResult(
            text="ok",
            duration_ms=1,
            input_tokens=None,
            output_tokens=None,
            cache_creation_input_tokens=None,
            cache_read_input_tokens=None,
        )
    )
    node = agent_node(operation="chat", model="claude-sonnet-5", prompt="hi")

    result = await node(NodeContext(state={}, node="chat", superstep=0, run_id="r1"))

    assert result.meta["tokens"] == 0


async def test_runtime_charges_agent_node_tokens_to_the_run_budget(fake_claude):
    fake_claude(
        _claude_result(
            "ok",
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=7,
            cache_read_input_tokens=3,
        )
    )
    graph = Graph("charged")
    graph.add_node(
        "chat",
        agent_node(operation="chat", model="claude-sonnet-5", prompt="hi"),
        kind="agent",
    )
    graph.set_entry("chat").set_finish("chat")

    budget = RunBudget()
    checkpointer = _cp()
    result = await run(graph, checkpointer=checkpointer, budget=budget)

    assert result.status == STATUS_COMPLETED
    assert budget.tokens == 160
    assert result.budget["tokens"] == 160

    step = checkpointer.steps(result.run_id)[0]
    assert step.tokens == 160
    assert step.kind == "agent"


async def test_parse_json_parses_the_reply(fake_claude):
    fake_claude(_claude_result('{"intent": "hot", "score": 0.9}'))
    node = agent_node(
        operation="qualify",
        model="claude-sonnet-5",
        prompt="hi",
        parse_json=True,
        output_key="qualification",
    )

    result = await node(NodeContext(state={}, node="qualify", superstep=0, run_id="r1"))

    assert result.updates == {"qualification": {"intent": "hot", "score": 0.9}}


async def test_parse_json_strips_code_fences(fake_claude):
    fake_claude(_claude_result('```json\n{"ok": true}\n```'))
    node = agent_node(
        operation="qualify", model="claude-sonnet-5", prompt="hi", parse_json=True
    )

    result = await node(NodeContext(state={}, node="qualify", superstep=0, run_id="r1"))

    assert result.updates == {"reply": {"ok": True}}


async def test_response_schema_implies_parse_json(fake_claude):
    fake = fake_claude(_claude_result('{"ok": true}'))
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    node = agent_node(
        operation="qualify",
        model="claude-sonnet-5",
        prompt="hi",
        response_schema=schema,
    )

    result = await node(NodeContext(state={}, node="qualify", superstep=0, run_id="r1"))

    assert result.updates == {"reply": {"ok": True}}
    assert fake.calls[0]["response_schema"] == schema


async def test_malformed_json_raises_value_error(fake_claude):
    fake_claude(_claude_result("this is not json at all"))
    node = agent_node(
        operation="qualify", model="claude-sonnet-5", prompt="hi", parse_json=True
    )

    with pytest.raises(ValueError) as exc:
        await node(NodeContext(state={}, node="qualify", superstep=0, run_id="r1"))
    message = str(exc.value)
    assert "node 'qualify' expected JSON" in message
    assert "this is not json at all" in message


async def test_malformed_json_is_subject_to_the_node_retry_policy(fake_claude):
    """The parse failure surfaces as a node error, so retries can rescue it."""
    fake = fake_claude(_claude_result("garbage"), _claude_result('{"ok": true}'))

    graph = Graph("json-retry")
    graph.add_node(
        "qualify",
        agent_node(
            operation="qualify", model="claude-sonnet-5", prompt="hi", parse_json=True
        ),
        kind="agent",
        retries=1,
        retry_backoff_seconds=0,
    )
    graph.set_entry("qualify").set_finish("qualify")

    checkpointer = _cp()
    result = await run(graph, checkpointer=checkpointer)

    assert result.status == STATUS_COMPLETED
    assert result.state["reply"] == {"ok": True}
    assert len(fake.calls) == 2
    assert checkpointer.steps(result.run_id)[0].attempts == 2


async def test_malformed_json_fails_the_run_without_retries(fake_claude):
    fake_claude(_claude_result("garbage"))

    graph = Graph("json-fail")
    graph.add_node(
        "qualify",
        agent_node(
            operation="qualify", model="claude-sonnet-5", prompt="hi", parse_json=True
        ),
        kind="agent",
    )
    graph.set_entry("qualify").set_finish("qualify")

    result = await run(graph, checkpointer=_cp())

    assert result.status == STATUS_FAILED
    assert "node 'qualify'" in result.error
    assert "ValueError" in result.error


async def test_updates_callable_fans_out_to_several_channels(fake_claude):
    fake_claude(_claude_result('{"intent": "hot", "score": 0.9, "why": "budget"}'))

    seen = {}

    def fan_out(state, parsed):
        seen["state"] = dict(state)
        seen["parsed"] = parsed
        return {
            "intent": parsed["intent"],
            "score": parsed["score"],
            "rationale": parsed["why"],
        }

    node = agent_node(
        operation="qualify",
        model="claude-sonnet-5",
        prompt="hi",
        parse_json=True,
        updates=fan_out,
    )

    result = await node(
        NodeContext(state={"lead_id": "L1"}, node="qualify", superstep=0, run_id="r1")
    )

    assert result.updates == {"intent": "hot", "score": 0.9, "rationale": "budget"}
    assert seen["state"] == {"lead_id": "L1"}
    assert seen["parsed"] == {"intent": "hot", "score": 0.9, "why": "budget"}


async def test_updates_callable_receives_raw_text_when_not_parsing(fake_claude):
    fake_claude(_claude_result("plain text reply"))
    node = agent_node(
        operation="chat",
        model="claude-sonnet-5",
        prompt="hi",
        updates=lambda state, value: {"a": value, "b": len(value)},
    )

    result = await node(NodeContext(state={}, node="chat", superstep=0, run_id="r1"))

    assert result.updates == {"a": "plain text reply", "b": len("plain text reply")}


async def test_budget_precheck_refuses_to_call_the_model_when_already_over(fake_claude):
    fake = fake_claude(_claude_result("should never be reached"))
    budget = RunBudget(max_tokens=100)
    budget.charge_tokens(150)

    node = agent_node(operation="chat", model="claude-sonnet-5", prompt="hi")
    ctx = NodeContext(
        state={},
        node="chat",
        superstep=0,
        run_id="r1",
        extras={"budget": budget},
    )

    with pytest.raises(BudgetExhausted) as exc:
        await node(ctx)

    assert exc.value.limit == "tokens"
    assert "node 'chat' refused to call" in str(exc.value)
    assert "150 of 100 tokens" in str(exc.value)
    assert fake.calls == [], "the model must not be called once the budget is spent"


async def test_budget_precheck_is_skipped_when_no_token_limit_is_set(fake_claude):
    fake = fake_claude(_claude_result("ok"))
    budget = RunBudget(max_tokens=None)
    budget.charge_tokens(10_000)

    node = agent_node(operation="chat", model="claude-sonnet-5", prompt="hi")
    await node(
        NodeContext(
            state={}, node="chat", superstep=0, run_id="r1", extras={"budget": budget}
        )
    )

    assert len(fake.calls) == 1


async def test_a_run_that_outspends_its_token_budget_ends_budget_exhausted(fake_claude):
    fake_claude(_claude_result("ok", input_tokens=50, output_tokens=0,
                               cache_creation_input_tokens=0,
                               cache_read_input_tokens=0))

    graph = Graph("token-capped")
    node_fn = agent_node(operation="chat", model="claude-sonnet-5", prompt="hi")
    graph.add_node("first", node_fn, kind="agent")
    graph.add_node("second", node_fn, kind="agent")
    graph.set_entry("first")
    graph.add_edge("first", "second")
    graph.set_finish("second")

    budget = RunBudget(max_tokens=10)
    result = await run(graph, checkpointer=_cp(), budget=budget)

    assert result.status == STATUS_BUDGET_EXHAUSTED
    assert result.budget["tokens"] == 50


def test_agent_node_names_itself_for_logs():
    node = agent_node(operation="qualify_lead", model="claude-sonnet-5", prompt="hi")
    assert node.__name__ == "agent_node[qualify_lead]"


# ===========================================================================
# adapters/tools.py
# ===========================================================================


def test_tool_registers_a_callable():
    @tool("crm.update_stage")
    def update_stage(*, lead_id):
        return {"lead_id": lead_id}

    assert registered() == ["crm.update_stage"]
    assert get_tool("crm.update_stage") is update_stage


def test_tool_returns_the_original_function_undecorated():
    @tool("noop")
    def fn():
        return "value"

    assert fn() == "value"


def test_duplicate_tool_registration_raises():
    @tool("crm.update_stage")
    def first():
        return None

    with pytest.raises(ValueError) as exc:
        @tool("crm.update_stage")
        def second():
            return None

    assert "tool 'crm.update_stage' is already registered" in str(exc.value)


def test_get_tool_on_an_unknown_name_lists_the_registered_ones():
    @tool("alpha")
    def alpha():
        return None

    @tool("beta")
    def beta():
        return None

    with pytest.raises(KeyError) as exc:
        get_tool("gamma")
    message = exc.value.args[0]
    assert "no tool registered as 'gamma'" in message
    assert "'alpha'" in message
    assert "'beta'" in message


def test_get_tool_on_an_empty_registry_says_none():
    with pytest.raises(KeyError) as exc:
        get_tool("gamma")
    assert "none" in exc.value.args[0]


def test_registered_is_sorted():
    for name in ("zeta", "alpha", "mu"):
        tool(name)(lambda: None)
    assert registered() == ["alpha", "mu", "zeta"]


def test_clear_empties_the_registry():
    tool("alpha")(lambda: None)
    tools_adapter.clear()
    assert registered() == []


async def test_tool_node_calls_a_sync_tool():
    @tool("math.double")
    def double(*, n):
        return n * 2

    node = tool_node("math.double", args=lambda s: {"n": s["n"]})
    result = await node(NodeContext(state={"n": 21}, node="double", superstep=0, run_id="r1"))

    assert result.updates == {"tool_result": 42}
    assert result.meta == {"tool": "math.double"}


async def test_tool_node_calls_an_async_tool():
    @tool("crm.fetch")
    async def fetch(*, lead_id):
        return {"id": lead_id, "stage": "new"}

    node = tool_node("crm.fetch", args=lambda s: {"lead_id": s["lead_id"]})
    result = await node(
        NodeContext(state={"lead_id": "L1"}, node="fetch", superstep=0, run_id="r1")
    )

    assert result.updates == {"tool_result": {"id": "L1", "stage": "new"}}


async def test_tool_node_args_callable_maps_state_to_kwargs():
    seen = {}

    @tool("echo")
    def echo(**kwargs):
        seen["kwargs"] = kwargs
        return kwargs

    def build_args(state):
        seen["state"] = dict(state)
        return {"lead_id": state["lead_id"], "stage": state["target_stage"]}

    node = tool_node("echo", args=build_args)
    await node(
        NodeContext(
            state={"lead_id": "L1", "target_stage": "qualified", "noise": 1},
            node="echo",
            superstep=0,
            run_id="r1",
        )
    )

    assert seen["state"] == {"lead_id": "L1", "target_stage": "qualified", "noise": 1}
    assert seen["kwargs"] == {"lead_id": "L1", "stage": "qualified"}


async def test_tool_node_defaults_to_no_arguments():
    @tool("ping")
    def ping():
        return "pong"

    node = tool_node("ping")
    result = await node(NodeContext(state={"ignored": True}, node="ping", superstep=0, run_id="r1"))

    assert result.updates == {"tool_result": "pong"}


async def test_tool_node_custom_output_key():
    @tool("ping")
    def ping():
        return "pong"

    node = tool_node("ping", output_key="pong_channel")
    result = await node(NodeContext(state={}, node="ping", superstep=0, run_id="r1"))

    assert result.updates == {"pong_channel": "pong"}


async def test_tool_node_updates_callable_fans_out():
    @tool("crm.fetch")
    def fetch():
        return {"id": "L1", "stage": "new"}

    node = tool_node(
        "crm.fetch",
        updates=lambda state, value: {"lead_id": value["id"], "stage": value["stage"]},
    )
    result = await node(NodeContext(state={}, node="fetch", superstep=0, run_id="r1"))

    assert result.updates == {"lead_id": "L1", "stage": "new"}


async def test_tool_node_resolves_the_tool_at_call_time():
    """A graph may be built before the module registering its tools imports."""
    node = tool_node("late.registered")

    with pytest.raises(KeyError):
        await node(NodeContext(state={}, node="late", superstep=0, run_id="r1"))

    @tool("late.registered")
    def late():
        return "now here"

    result = await node(NodeContext(state={}, node="late", superstep=0, run_id="r1"))
    assert result.updates == {"tool_result": "now here"}


def test_tool_node_names_itself_for_logs():
    assert tool_node("crm.update_stage").__name__ == "tool_node[crm.update_stage]"


async def test_tool_node_inside_a_run():
    @tool("crm.fetch")
    async def fetch(*, lead_id):
        return {"id": lead_id}

    graph = Graph("tooling")
    graph.add_node(
        "fetch",
        tool_node("crm.fetch", args=lambda s: {"lead_id": s["lead_id"]}),
    )
    graph.set_entry("fetch").set_finish("fetch")

    checkpointer = _cp()
    result = await run(graph, {"lead_id": "L9"}, checkpointer=checkpointer)

    assert result.status == STATUS_COMPLETED
    assert result.state["tool_result"] == {"id": "L9"}
    assert checkpointer.steps(result.run_id)[0].meta == {"tool": "crm.fetch"}
