# Implementation Summary — 2026-04-05

## Scope
This pass covered three major tracks:
1. safety-first hardening
2. agent/control-plane cleanup
3. runtime AI centralization + prompt hardening follow-through

## Safety-first changes

### `.mcp.json`
- Removed the committed raw Supabase MCP token pattern
- Replaced the tracked value with environment-variable interpolation
- Operational note: the old token should still be rotated

### `backend/mcp_server.py`
- Tightened MCP auth boundary
- Dedicated MCP API keys are now required
- Widget API keys are no longer accepted for MCP access
- Updated tool descriptions and error messaging to reflect dedicated MCP keys

### `backend/routers/widget_booking.py`
- Added stricter validation for model-driven `ORDER_JSON` payloads
- Added stricter validation for model-driven `BID_REQUEST` payloads
- Added accepted-payload logging for traceability
- Rejected malformed, inconsistent, or under-specified structured payloads before side effects occur

## Docs / control-plane cleanup

### Added
- `docs/AI_ARCHITECTURE_AUDIT.md`
- `docs/AGENT_SYSTEM_PLAN.md`

### Updated
- `.ai/manifest.json`
- `AGENTS.md`

### Outcomes
- clearer canonical hierarchy for repo-agent resources
- explicit Codex / Anthropic / MiniMax role split
- machine-readable manifest now better reflects current repo reality
- `AGENTS.md` reduced to a thin adapter rather than a second drifting brain

## Runtime AI centralization

### Shared runtime wrapper
All remaining app-level Anthropic call sites were moved behind:
- `backend/services/llm_runtime.py`

### Updated modules
- `backend/services/content_repurposer.py`
- `backend/services/automation_engine.py`
- `backend/routers/content.py`
- `backend/routers/snippets.py`
- `backend/routers/reviews.py`
- `backend/routers/marketing_campaigns.py`
- `backend/routers/menu.py`
- `backend/routers/jobs.py`
- `backend/routers/bids.py`
- `backend/routers/leads.py`
- `backend/routers/social_media.py`
- `backend/routers/analytics.py`
- `backend/routers/onboarding.py`
- `backend/routers/local_seo.py`
- `backend/routers/twilio_webhooks.py`

### Result
After the migration, the only direct Anthropic client usage remaining under `backend/` is the wrapper itself in `backend/services/llm_runtime.py`.

## Widget prompt hardening

### `backend/routers/widget_helpers.py`
Changes:
- added shared sanitization for untrusted/reference prompt text
- added explicit reference-block formatting
- kept platform-owned rules at the top of the prompt
- stopped promoting tenant `custom_instructions` into the top identity slot
- delimited business/crawled/generated/reference content more clearly

### Prompt-fed sources hardened
- custom instructions
- FAQs
- owner corrections
- crawled website content
- knowledge base text
- menu items
- job listings
- bid templates
- custom field definitions
- flow node text

## Testing / verification

### Static verification performed
- repeated `python -m py_compile` runs across changed backend modules
- JSON validation for `.mcp.json` and `.ai/manifest.json`
- global grep to confirm app-level Anthropic calls were centralized

### Targeted behavior checks performed
- valid/invalid order payload acceptance and rejection
- valid/invalid bid payload acceptance and rejection

### Added focused tests
- `tests/test_ai_runtime_hardening.py`
  - structured payload validation
  - widget prompt trust-boundary assertions
  - wrapper-centralization assertions on selected routes

## Remaining recommended work
1. rotate the previously exposed Supabase token
2. ensure `SUPABASE_ACCESS_TOKEN` exists in the real MCP runtime environment
3. expand automated coverage around:
   - onboarding response parsing
   - local SEO JSON parsers
   - Twilio SMS AI path
   - widget prompt-builder regressions
4. consider stronger source labeling / sanitization policy for crawled content and admin-authored reference text
5. improve structured metrics/logging inside `llm_runtime.py`

## Bottom line
This pass materially improved:
- secret handling
- auth boundary separation
- model-output side-effect safety
- prompt trust boundaries
- runtime AI control-plane centralization
- agent documentation clarity for future work
