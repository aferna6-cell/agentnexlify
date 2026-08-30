"""Declarative roster for the Slack agent team + deterministic routing.

One Slack app hosts several agents. Each agent is a persona: its own
display name and icon (posted via ``chat.postMessage`` username/icon
overrides) plus its own mandate in the system prompt. Adding a teammate
means adding one ``SlackAgent`` entry here — no router or service change.

Routing is deterministic (keyword regex over the message, highest match
count wins), not an LLM classifier: a classifier would double the cost
and latency of every message and is impossible to unit-test for drift.
Same reasoning as ``connector_registry.infer_needed_connectors``.

Business context lives in this module rather than being read from
``CLAUDE.md`` because ``backend/Dockerfile`` only copies ``backend/``,
``widget/``, and ``VERSION`` into the image — the repo's markdown is not
on disk in production. Keep ``_PLATFORM_CONTEXT`` in sync with CLAUDE.md
when plans, stack, or schema invariants change.
"""

import re
from dataclasses import dataclass, field

# Sourced from CLAUDE.md (WHAT/WHY sections). Deliberately compact: it is
# prepended to every agent's system prompt, so every line is paid for on
# every message.
_PLATFORM_CONTEXT = """\
AgentNexLiFy is a multi-tenant AI business-automation SaaS for small businesses.
An embeddable chat widget captures leads, books appointments, and runs
follow-ups; a React dashboard is the operator surface.

Stack: FastAPI + Python 3.11 backend on Railway, Supabase Postgres with RLS,
React 18 + Vite dashboard on Vercel, Anthropic Claude for AI, Resend for email,
Twilio for SMS/voice, Stripe for billing.

Plans: `chatbot` $19.99/mo (widget and chat only), `agent_os` $99.99/mo (full
platform), managed `agent_os` $299.99/mo plus $199 setup. `free` is an internal
lapsed state, never sold. Retired names never to use: foundation, operations.

Schema invariants: `leads` and `conversations` are scoped by `client_id`, never
`tenant_id`. Lead status lives in `status`, never `lead_stage`. Lead interests
live in `areas_of_interest`, never `service_interest`. Schema changes only via
numbered files in `migrations/`.

Main competitor is GoHighLevel ($97-497/mo). The differentiator is widget-first
onboarding with a per-tenant vertical knowledge base, not a generic LLM reply.
"""

# Every agent inherits these. Slack renders `mrkdwn`, not full Markdown:
# headings and tables do not exist, so asking for them produces literal
# `##` in the channel.
_SHARED_STYLE = """\
You are one member of a small agent team that lives in the founder's Slack
workspace. You answer in-channel, in a thread.

Format for Slack mrkdwn: no headings, no tables, no code fences unless you are
quoting code. `*bold*` (single asterisks), `_italic_`, and `•` bullets. Keep it
under 1200 characters unless asked for depth. No greeting, no preamble, no
sign-off, no restating the question.

You have no tools: you cannot query the database, read the repository, call the
API, or change anything. You answer from this thread and your own knowledge.
When a correct answer needs live data or the actual source, say so in one line
and name the exact file, table, or dashboard to check. Never invent a file path,
column name, metric, or customer fact. "I don't know, check X" is a good answer.
"""


@dataclass(frozen=True)
class SlackAgent:
    key: str
    display_name: str
    emoji: str
    # One-line summary shown by the `help` command.
    tagline: str
    # Persona-specific half of the system prompt.
    mandate: str
    aliases: tuple[str, ...] = ()
    patterns: tuple[str, ...] = field(default_factory=tuple)

    def system_prompt(self) -> str:
        return (
            f"You are {self.display_name}, {self.tagline}\n\n"
            f"{self.mandate}\n\n"
            f"--- Platform context ---\n{_PLATFORM_CONTEXT}\n"
            f"--- Style ---\n{_SHARED_STYLE}"
        )


# Order is load-bearing: it breaks routing score ties and sets the order of
# the `help` listing and team fan-out. `chief` is first because it is the
# fallback when nothing matches.
_ROSTER: tuple[SlackAgent, ...] = (
    SlackAgent(
        key="chief",
        display_name="Chief of Staff",
        emoji=":necktie:",
        tagline="the founder's chief of staff.",
        mandate=(
            "You handle anything that is not clearly one specialist's lane: "
            "priorities, trade-offs, sequencing, and 'what should I do next'. "
            "Lead with a recommendation, then at most three reasons. When a "
            "question really belongs to a teammate, answer briefly and say "
            "which teammate to ask (for example: 'ask schema')."
        ),
        aliases=("cos", "chief-of-staff", "coordinator"),
        # Deliberately narrow. Broad phrasing like "should I ..." would
        # hijack questions that belong to a specialist ("should I raise the
        # chatbot price?" is growth's call), and the chief already catches
        # everything no other agent matches.
        patterns=(
            r"\b(priorit(y|ies|ise|ize)|roadmap|trade[- ]?off)\b",
            r"\bwhat should i (do|work on|focus on|build|ship)\b",
            r"\b(next step|biggest (risk|lever)|where should i)\b",
        ),
    ),
    SlackAgent(
        key="engineer",
        display_name="Engineer",
        emoji=":hammer_and_wrench:",
        tagline="the platform engineer for backend, dashboard, and widget code.",
        mandate=(
            "You cover FastAPI routers and services, the React/Vite dashboard, "
            "and the embeddable widget. Two hard rules you always enforce: "
            "never `from __future__ import annotations` in FastAPI files (it "
            "makes Pydantic 422 every request), and the widget JS must stay "
            "byte-identical across `widget/`, `frontend/public/widget/`, and "
            "`landing-page-v2/widget/`. Prefer the smallest change that fixes "
            "the observed problem; name the file to open first."
        ),
        aliases=("eng", "dev", "backend", "frontend"),
        patterns=(
            r"\b(bug|stack ?trace|traceback|exception|422|500|regression)\b",
            r"\b(endpoint|router|pydantic|fastapi|react|vite|component)\b",
            r"\b(widget|embed) (js|script|snippet|code)\b",
            r"\b(refactor|test coverage|unit test|pytest|vitest)\b",
        ),
    ),
    SlackAgent(
        key="schema",
        display_name="Schema Guardian",
        emoji=":shield:",
        tagline="the guardian of the Supabase schema.",
        mandate=(
            "You cover tables, columns, migrations, RLS, and tenant scoping. "
            "Restate the relevant invariant before answering, because this "
            "codebase has shipped `tenant_id`/`client_id` bugs three times. "
            "Every schema change is a new numbered file in `migrations/` "
            "plus a `docs/dev-knowledge/schema-log.md` entry — never ad-hoc "
            "SQL. Flag any query you are shown that is not tenant-scoped."
        ),
        aliases=("db", "database", "sql", "migration", "schema-guardian"),
        patterns=(
            r"\b(schema|migration|column|table|index|rls|postgres|supabase)\b",
            r"\b(client_id|tenant_id|lead_stage|areas_of_interest)\b",
            r"\b(query|select|insert|update)\b[^.?!]{0,30}\b(leads|conversations|tenants)\b",
        ),
    ),
    SlackAgent(
        key="growth",
        display_name="Growth",
        emoji=":chart_with_upwards_trend:",
        tagline="the growth and positioning lead.",
        mandate=(
            "You cover pricing, packaging, positioning, competitors, landing "
            "pages, SEO, and churn. Anchor every answer to the real plan "
            "prices and to the widget-first differentiator against "
            "GoHighLevel. Give one concrete next action a solo founder can "
            "actually ship, not a campaign plan that needs a team."
        ),
        aliases=("marketing", "sales", "gtm"),
        patterns=(
            r"\b(pricing|price|packaging|plan tier|upsell|paywall)\b",
            r"\b(competitor|gohighlevel|ghl|podium|birdeye|drillbit)\b",
            r"\b(positioning|messaging|landing page|seo|funnel|churn|cac|ltv)\b",
            r"\b(cold email|outreach|campaign|ad copy)\b",
        ),
    ),
    SlackAgent(
        key="support",
        display_name="Support",
        emoji=":headphones:",
        tagline="the customer-facing support lead.",
        mandate=(
            "You cover tenant-reported problems: the widget not answering, "
            "leads not landing, appointments not booking, billing confusion, "
            "escalations. Split every answer into what to tell the customer "
            "now and what to check on our side. Ask for the tenant name or "
            "`client_id` when the answer depends on it — do not guess which "
            "tenant is affected."
        ),
        aliases=("cs", "customer", "helpdesk"),
        patterns=(
            r"\b(customer|tenant|client) (is|reports?|says?|complain|asked)\b",
            r"\b(not (working|answering|capturing|booking|sending)|broken|stuck)\b",
            r"\b(refund|cancel(led)? (subscription|account)|escalat(e|ion))\b",
            r"\b(onboarding|trial) (issue|problem|question)\b",
        ),
    ),
    SlackAgent(
        key="ops",
        display_name="Ops",
        emoji=":satellite:",
        tagline="the deploy, monitoring, and incident lead.",
        mandate=(
            "You cover Railway (backend), Vercel (frontend and marketing "
            "site), environment variables, uptime, alerting, and incidents. "
            "During an incident lead with the single fastest way to confirm "
            "or rule out the suspected cause, then the rollback. Name the "
            "exact dashboard, endpoint, or log query to look at."
        ),
        aliases=("devops", "infra", "sre"),
        patterns=(
            r"\b(deploy|deployment|rollback|railway|vercel|docker|build fail)\b",
            r"\b(uptime|downtime|outage|incident|healthz|health check|alert)\b",
            r"\b(env var|environment variable|secret|api key rotation)\b",
            r"\b(logs?|latency|timeout|502|503|504)\b",
        ),
    ),
)

_BY_KEY = {agent.key: agent for agent in _ROSTER}
_BY_LABEL = {
    label: agent
    for agent in _ROSTER
    for label in (agent.key, *agent.aliases)
}
_COMPILED = {
    agent.key: tuple(re.compile(p, re.IGNORECASE) for p in agent.patterns)
    for agent in _ROSTER
}

DEFAULT_AGENT_KEY = "chief"

# Labels that fan a question out to several agents at once.
_TEAM_LABELS = frozenset({"team", "all", "everyone", "council", "war room"})
_HELP_WORDS = frozenset({"help", "who", "roster", "agents", "?"})

# Slack wraps user/group mentions in angle brackets: <@U123>, <!subteam^S1>,
# <!here>. Strip them so a mention never leaks into the prompt or gets
# mistaken for an agent label.
_MENTION_TOKEN = re.compile(r"<[@!#][^>]*>")
_AGENT_PREFIX = re.compile(r"^([A-Za-z][A-Za-z0-9 _,-]{0,30})\s*:\s*(.+)$", re.DOTALL)

# How many agents answer a `team:` question. Three is enough for genuinely
# different angles and bounds the per-message cost at 4 model calls
# (3 agents + the chief's synthesis).
TEAM_FANOUT = 3


@dataclass(frozen=True)
class SlackCommand:
    """Parsed intent of one inbound Slack message.

    ``kind``:
      - ``"help"``  — print the roster, no model call.
      - ``"ask"``   — one agent answers (``agent_keys`` has one entry).
      - ``"team"``  — several agents answer, then the chief synthesizes.
    """

    kind: str
    agent_keys: tuple[str, ...]
    question: str
    # True when the caller named the agent explicitly, so thread
    # continuation must not silently override the choice.
    explicit: bool = False


def get_agent(key: str) -> SlackAgent | None:
    return _BY_KEY.get(key)


def roster() -> tuple[SlackAgent, ...]:
    return _ROSTER


def resolve_label(label: str) -> SlackAgent | None:
    """Resolve an agent key, alias, or display name. Case/space-insensitive."""
    normalized = " ".join(label.strip().lower().split())
    if not normalized:
        return None
    direct = _BY_LABEL.get(normalized)
    if direct:
        return direct
    return next(
        (a for a in _ROSTER if a.display_name.lower() == normalized), None
    )


def strip_mentions(text: str) -> str:
    return " ".join(_MENTION_TOKEN.sub(" ", text or "").split())


def route(text: str) -> str:
    """Pick the best agent for ``text``. Falls back to the chief.

    Score is the number of that agent's patterns which match, so a message
    hitting two schema patterns beats one hitting a single ops pattern.
    Ties go to declaration order.
    """
    if not text:
        return DEFAULT_AGENT_KEY
    best_key = DEFAULT_AGENT_KEY
    best_score = 0
    for agent in _ROSTER:
        score = sum(1 for p in _COMPILED[agent.key] if p.search(text))
        if score > best_score:
            best_key, best_score = agent.key, score
    return best_key


def route_many(text: str, limit: int = TEAM_FANOUT) -> tuple[str, ...]:
    """Agents most relevant to ``text``, best first, padded to ``limit``.

    Used by `team:` fan-out. Padding keeps a vague question from being
    answered by a single agent when the caller explicitly asked the team:
    unmatched agents are appended in declaration order.
    """
    scored = [
        (sum(1 for p in _COMPILED[a.key] if p.search(text or "")), i, a.key)
        for i, a in enumerate(_ROSTER)
    ]
    matched = [key for score, _, key in sorted(scored, key=lambda s: (-s[0], s[1])) if score]
    padded = matched + [a.key for a in _ROSTER if a.key not in matched]
    return tuple(padded[:limit])


def parse_command(raw_text: str) -> SlackCommand:
    """Turn raw Slack message text into a :class:`SlackCommand`.

    Grammar (after mentions are stripped):
      - ``help`` / ``who`` / ``agents`` / empty  -> help
      - ``<agent>: question``                    -> that agent answers
      - ``team: question``                       -> fan-out + synthesis
      - anything else                            -> auto-routed

    An unrecognized ``word:`` prefix is NOT an error — "Note: the widget
    is down" is a question, not a typo'd agent name — so the whole text
    falls through to auto-routing.
    """
    text = strip_mentions(raw_text)
    if not text:
        return SlackCommand(kind="help", agent_keys=(), question="")

    if text.strip().lower().rstrip("?!.") in _HELP_WORDS:
        return SlackCommand(kind="help", agent_keys=(), question="")

    match = _AGENT_PREFIX.match(text)
    if match:
        label, remainder = match.group(1).strip(), match.group(2).strip()
        normalized = " ".join(label.lower().split())
        if normalized in _TEAM_LABELS and remainder:
            return SlackCommand(
                kind="team",
                agent_keys=route_many(remainder),
                question=remainder,
                explicit=True,
            )
        agent = resolve_label(label)
        if agent and remainder:
            return SlackCommand(
                kind="ask",
                agent_keys=(agent.key,),
                question=remainder,
                explicit=True,
            )

    return SlackCommand(kind="ask", agent_keys=(route(text),), question=text)


def help_text(bot_handle: str = "@nexus") -> str:
    """Roster listing. Deterministic — never costs a model call."""
    lines = [
        (
            "*The team.* Mention me and I route automatically, or name an "
            f"agent: `{bot_handle} schema: does leads have tenant_id?`"
        ),
    ]
    lines += [
        f"{a.emoji} *{a.display_name}* (`{a.key}`) — {a.tagline}" for a in _ROSTER
    ]
    lines.append(
        f"`{bot_handle} team: <question>` — {TEAM_FANOUT} agents answer, "
        "then the chief synthesizes."
    )
    lines.append("In a DM you can drop the mention. Replies stay in-thread.")
    return "\n".join(lines)
