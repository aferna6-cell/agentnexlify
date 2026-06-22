# Audit — Stale Facts in Live Docs (2026-06-22)

**Scope:** Audit authoritative/live documentation for factually stale claims and
correct them. Dated historical records (daily-logs, nightly-reviews, dated
audits, content, knowledge-base, brain, specs, plans) were left as point-in-time
records; for dated planning docs, corrections were appended as markers rather
than overwriting history.

**Branch:** `claude/stale-fact-audit` (off `claude/agent-nexlify-testing-28d597`)

## Ground truth used
- Current paid plans: `chatbot` ($19.99/mo) + `agent_os` ($99.99/mo). `free` =
  internal lapsed state. Legacy grandfathered: growth/autopilot/professional/enterprise.
  Retired names (never use): foundation/operations. Repriced 2026-06-15.
- Weekly value digest (gap "G2") SHIPPED: `backend/services/weekly_value.py::compute_weekly_value`
  + `backend/services/automation/scheduled_jobs_ext.py::send_weekly_digest`.
- Marketing Suite add-on RETIRED (PR #228); migration 137 dropped `marketing_addon_*` columns.
- Agent OS merged to production 2026-06-09.
- Highest migration number: **154**.
- Valid Claude model IDs: `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`.

## Corrected (this audit)

| File | What was stale | Correction |
|------|----------------|------------|
| `CLAUDE.md` | Key directories said migrations "numbered 001–102+" | → `001–154+` |
| `docs/dev-knowledge/canonical-schema.md` | Header `Migration number: 106`; `Last updated: 2026-04-18` | → `154`; `2026-06-22` |
| `docs/dev-knowledge/canonical-schema.md` | `plan` column notes listed only `free/growth/professional/autopilot/enterprise` | Added current paid (chatbot/agent_os) + legacy framing |
| `docs/managed-agents.md` | Recommended `claude-opus-4-6` (legacy) for code-review flows | → `claude-opus-4-7` |
| `docs/MARKETING_ADDON.md` | Entire file presented retired add-on as a live $49.99/mo product + told new deploys to apply migration 102 (columns later dropped by 137) | Prepended RETIRED banner (do-not-follow, body kept as historical record) |
| `docs/env-vars-2026-04-26.md` | Rate-limit vars listed only legacy tiers; `chatbot`/`agent_os` silently fall back to free-tier 30 rpm (verified in `rate_limit.py`) | Added note + `RATE_LIMIT_CHATBOT_RPM`/`RATE_LIMIT_AGENT_OS_RPM` |
| `planning/gap-analysis-small-business-2026-06-10.md` | G2 marked "HIGHEST OPEN"; sequence item 1 = "G2 weekly value digest" | Appended SHIPPED markers (G2 + sequence) — history preserved |
| `planning/gap-analysis-small-business-2026-06-10.md` | G5 cited canonical pricing growth $99 / autopilot $150 / professional $250 / enterprise $899 | Appended marker: repricing 2026-06-15 → chatbot $19.99 + agent_os $99.99; old prices legacy-only |
| `planning/launch-readiness-rubric.md` | Dimension 3 presented plan universe entirely in legacy terms | Appended plan-lineup note (evidence rows left intact — tests genuinely cover legacy grandfathered flows) |

## Intentionally NOT changed (dated historical artifacts — accurate as point-in-time records)
- `docs/CODEBURN.md` — 2026-04-15 cost snapshot ("Opus 4.6 99%"); accurate for its date (pre-4.7 launch).
- `docs/CLAUDE_SKILLS_RESEARCH.md` — pricing figures appear to quote external/competitor research, not our lineup; low confidence, left to avoid misrepresenting source.
- `docs/agent-os-rehaul-partner-brief.md` — dated 2026-05-25 forward-looking brief ("$250/mo Pro"); pre-prod planning artifact.
- `planning/stress-test-2026-04-17.md` — dated artifact already self-flagged stale; left as record.
- Test-evidence row `launch-readiness-rubric.md:3.7` — accurately describes what `test_checkout_trial_to_paid.py` asserts (legacy flows); not falsified (user-rules Rule 10).

## Confirmed clean (no factual staleness)
- All `.claude/rules/*.md` (model IDs valid; `claude-opus-4-6` only ever framed as legacy).
- `AGENTS.md`, `README.md`, `STRUCTURE.md`, `KARPATHY.md`, `planning/CONTEXT.md`, `planning/vertical-positioning-2026-04-18.md`.
- `docs/dev-knowledge/schema-log.md` (latest = migration 154, applied 2026-06-18).
- `docs/dev-knowledge/{customer-gaps,test-coverage,architecture-decisions}.md`.

## Follow-up (out of scope — code, not docs)
- `backend/middleware/rate_limit.py::_TIER_DEFAULTS` has no entry for `chatbot`/`agent_os`;
  current plans fall back to free-tier 30 rpm unless env vars set. Worth a code fix +
  test (`backend/tests/test_plan_gating_new_plans.py`).
