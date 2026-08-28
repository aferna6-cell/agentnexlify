# AgentNexLiFy

AgentNexLiFy is an AI front desk and lead-capture platform for small service
businesses. It provides an embeddable website chat widget, onboarding tools,
conversation and lead workflows, and an agent-assisted development control
plane for maintaining the product.

## What It Does

- Answers routine visitor questions through a branded website widget.
- Captures lead details and conversation context.
- Helps business owners configure services, FAQs, hours, and widget styling.
- Supports follow-up workflows across dashboard, CRM, appointments, and automations.
- Maintains repo-level agent skills, autopilot issue workflows, and local quality gates.

## Local Quick Start

### Prerequisites

- Node.js and npm.
- Python 3.12. On this workstation, use `.venv312`.
- Supabase project credentials.
- Anthropic API key.

### Setup

```powershell
cp .env.example .env
python scripts/run_python.py
.venv312\Scripts\python.exe -m pip install -r backend\requirements.txt
npm install
npm --prefix frontend install
```

Edit `.env` with local keys before running the app.

### Run Locally

```powershell
npm run dev:backend
npm run dev:frontend
```

Backend defaults to `http://localhost:8000`. The frontend dev server uses the
frontend package configuration.

## Local Verification

Use the local release checklist when GitHub Actions minutes are unavailable:

- [Local Release Checklist](docs/LOCAL_RELEASE_CHECKLIST.md)
- [Autopilot Workflow](docs/AUTOPILOT_WORKFLOW.md)
- [Agent Routing Policy](docs/AGENT_ROUTING.md)
- [Sales Demo Script](docs/SALES_DEMO_SCRIPT.md)
- [Client Starter Kit](docs/client-starter-kit.md)

Common local gate:

```powershell
npm run check:local-release
```

That runs the quick agent checks, frontend build, focused backend tests for the
agent/autopilot surfaces, and frontend tests. The full backend suite is still
available with `npm run test:backend`, but it currently exposes stale test
mocks in older auth, onboarding, and local SEO coverage.

Individual gates:

```powershell
npm run check:quick
npm run build
npm run test:backend:focused
npm run test:frontend
```

`npm run check:quick` validates the agent system, skill metadata, canonical
skill sync, project invariants, widget mirrors, and Codex orchestration config.

## Local-Only Autopilot

When Actions are paused, use dry-run mode to classify issues without mutating
GitHub state:

```powershell
npm run autopilot:dry-run
npm run autopilot:dry-run:issue -- 123
```

Dry-run mode does not label, dispatch Codex, push, comment, or open pull
requests. It requires `gh` to be installed and authenticated.

## Widget Embed

Add this script to a customer website:

```html
<script
  src="https://your-domain.com/widget/agentnexlify-widget.js"
  data-api-key="anx_xxxxx"
  async>
</script>
```

Optional attributes:

- `data-brand-color="#00BFFF"`
- `data-api-base="https://api.agentnexlify.com"`

See [Client Starter Kit](docs/client-starter-kit.md) for platform-specific
installation steps.

## Architecture

```text
Website widget -> FastAPI backend -> LLM runtime wrapper -> Supabase
                                  -> notifications and integrations
Dashboard frontend -> API routes -> CRM, conversations, onboarding, billing
Agent system -> skills, checks, autopilot workflow, local verification
Agent OS engine (agent-service) -> departments -> action layer -> tools
```

The Agent OS engine lives in `agent-service/src/agent-os/` (pure compute; the
FastAPI data plane assembles its context and persists its results). When an
agent needs to *do* something rather than draft something, it goes through the
action layer: a typed tool registry, a central risk/approval policy, one
executor, verification, and an audit row per attempt. See
[Agent OS action layer](docs/agent-os-action-layer.md).

## Key Commands

```powershell
npm run check:quick
npm run check:local-release
npm run eval:agent-routing
npm run build
npm run test
npm run smoke
npm run sync-skills
npm run sync-widget
```

All Python npm scripts route through `scripts/run_python.py`, which prefers
`.venv312` and avoids accidentally using an incompatible system Python.
