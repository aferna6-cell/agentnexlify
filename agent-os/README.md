# Agent OS

An orchestrator that routes a small-business owner's plain-language asks to one
of **18 specialist worker agents**, each of which drafts channel-appropriate
output grounded in the owner's real business profile.

Self-contained: no database, no external services, no API key required. Runs in
the terminal and the browser. Drops into the wider AgentNexLiFy repo later, but
demos on its own today.

```
owner ask ──▶ Orchestrator (7 routing rules) ──▶ Worker agent ──▶ grounded draft
                     │                                  │
                     └── bucket listing / wishlist      └── honest reasoning trace
```

## Quickstart

```bash
cd agent-os
pip install -r requirements.txt    # or: make install

make demo                          # terminal walkthrough of every routing path
make api                           # http://localhost:8000  (API + web client)
make test                          # 132 tests
```

Single ask from the terminal:

```bash
python -m agent_os.demo.cli "follow up with Mike on the \$1,100 brake job quote I sent"
python -m agent_os.demo.cli --interactive
```

The demo runs **fully offline** on a deterministic provider — every agent still
produces grounded, rule-clean drafts. Set `ANTHROPIC_API_KEY` (and
`pip install anthropic`) to upgrade drafts to live Claude output; nothing else
changes.

## The three architectural rules

These are enforced at the **registry level**, not by convention. Importing
`agent_os.agents` runs static validation on every agent; `AgentRegistry.run`
re-validates every output at execution time. A violating agent fails CI — it can
never ship.

1. **Honest reasoning traces.** A "loaded" step reflects what actually loaded.
   No agent claims to have read the business profile or customer history when it
   didn't. Rule code: `honest_trace`.
2. **No bracketed placeholders** for fields that exist in the business profile.
   Customer-facing and sequence channels carry zero placeholders. A missing
   value surfaces to the owner in orchestrator chat — never into a customer
   draft. Rule codes: `placeholder`, `empty_draft`.
3. **Every agent declares its channel and respects channel formatting.**
   `sms` / `post` / `widget_reply` stay plain text; `email` / `report` /
   `sequence` / `internal` may use markdown. Rule code: `channel_format`.

## The 18 agents (8 buckets)

| Bucket | Agent | Channel | Status |
|---|---|---|---|
| customer_service | `customer_question` | widget_reply | existing |
| customer_service | `complaint_handler` | widget_reply | new |
| sales | `lead_nurture` | sequence | existing |
| sales | `quote_follow_up` | sequence | new |
| marketing | `campaign` | email | existing |
| marketing | `content_writer` | report | new |
| marketing | `social_post` | post | new |
| marketing | `seo_recommendations` | report | workaround |
| scheduling_ops | `booking` | sms | existing |
| scheduling_ops | `appointment_reminder` | sms | new |
| finance | `quote_generator` | email | new |
| finance | `invoice_reminder` | email | new |
| finance | `payment_follow_up` | sequence | new |
| reputation | `review_request` | sms | new |
| reputation | `ai_visibility_stub` | report | stub |
| reporting | `weekly_briefing` | report | new |
| system | `lead_triage` | internal | new |
| system | `generalist` | report | new |

Buckets are an internal maintenance construct — owners never see them, though
the orchestrator can list them on request ("what marketing agents do you have?").

## Routing rules (§11)

The orchestrator applies seven rules, in priority order:

1. **Confidence floor** — below threshold → `generalist`, and the ask is logged
   to the wishlist as demand for an agent that doesn't exist yet.
2. **Ambiguity gap** — two specialists score within a hair of each other → ask
   the owner to choose instead of guessing.
3. **Owner override** — the owner can reroute any decision to a named agent.
4. **Channel inference** — "text Carlos…" → `sms`, "email Dana…" → `email`.
5. **Specialty preference** — a dollar amount plus "quote" beats generic
   follow-up and routes to `quote_follow_up`.
6. **Complaint short-circuit** — anger/complaint language jumps straight to
   `complaint_handler` and flags it for the owner.
7. **Bucket awareness** — "what can you do?" returns the bucket listing, runs no
   agent.

## Layout

```
agent_os/
  schema.py          AgentSpec + enums (Bucket, Channel, Status, …)
  registry.py        registration-time + runtime rule enforcement
  rules.py           the three rules, with stable violation codes
  orchestrator.py    the seven routing rules
  base.py            BaseAgent (self-validates output too — defense in depth)
  profile.py         BusinessProfile (the grounding data)
  context.py         SharedContext (leads, appointments, widget chats, KB)
  llm.py             DeterministicProvider + AnthropicProvider
  channels.py        per-channel formatting rules
  placeholders.py    bracket detection
  trace.py           honest reasoning trace
  wishlist.py        demand capture for missing agents
  agents/            the 18 worker agents, grouped by bucket
  tools/seo_check.py offline on-page SEO checker
  demo/cli.py        terminal demo
  api/app.py         FastAPI surface (serves web/ at /)
web/index.html       static browser client
tests/               132 tests, including negative rule-violation tests
```

## Tests

```bash
make test            # python -m pytest -q
```

The suite includes **negative tests** that prove the rules actually reject bad
agents: a stub agent emitting an SMS placeholder, one emitting markdown on a
plain-text channel, one faking a load step — each is blocked by the registry.

## License

MIT.
