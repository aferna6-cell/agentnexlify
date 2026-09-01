# Winning Concept — Run 115 (2026-09-01)

## Recommendation
File a GH issue with `ai-ready` label to add a Haiku CRM field-omission guard in `agent-service/src/agent-os/agents/_extract.ts` — validate required CRM fields (name, email, status) after Haiku extraction rather than backfilling them downstream in `admin_records_actions.ts`.

## Why This, Why Now
Two PRs in two days (#726 merged 2026-08-31, #727 merged 2026-09-01) both fix the same bug class: Haiku omitting required CRM fields (name, email, status) in CRM intent extraction. Both patches land in `admin_records_actions.ts` — the consumer — as backfill logic. This is the third-plus occurrence of this class. Root cause: `_extract.ts` does not enforce CRM field contracts after Haiku extraction. Each missed field generates a new PR. Filing a GH issue with ai-ready label routes this to the issue-to-pr-loop for implementation — no production risk today, correct layer targeted, recurrence-terminating if guard lands.

## Evidence
- PR #726 (2026-08-31): backfill `name`/`email` when Haiku omits them from CRM intent
- PR #727 (2026-09-01): backfill `status` when Haiku omits it from CRM intent
- Pattern: same file, same class, consecutive days — indicates systemic gap not one-off
- `admin_records_actions.ts`: 427 lines (healthy) but accumulating backfill logic each cycle
- `_extract.ts` is the correct semantic layer — it extracts typed intent fields before passing to action handlers
- No schema migration required — guard is pure TypeScript validation logic

## Implementation Sketch
1. File GH issue via `mcp__github__issue_write`:
   - Title: `fix(agent-os): add CRM field-omission guard in _extract.ts — validate name/email/status post-Haiku extraction`
   - Labels: `bug`, `agent-os`, `ai-ready`
   - Body:
     ```
     ## Problem
     Haiku classification omits required CRM fields (name, email, status) in CRM intents.
     Downstream consumer admin_records_actions.ts backfills them (PRs #726, #727 — 2 fixes in 2 days, same class).
     
     ## Root cause
     _extract.ts does not enforce required field contracts after Haiku extraction.
     
     ## Fix
     In agent-service/src/agent-os/agents/_extract.ts:
     - For CRM intent extractions, add post-extraction validation step
     - If required fields (name, email, status) are absent: log a structured warning with the raw Haiku output, and either throw a typed ExtractValidationError or return a typed ExtractWarning that the caller can handle gracefully
     - Do NOT silently pass incomplete data downstream
     
     ## Acceptance criteria
     - Unit tests: CRM extraction with missing name/email/status raises ExtractValidationError
     - Integration tests: admin_records_actions.ts receives complete CRM fields or surfaces the error
     - No regression: non-CRM intent types unaffected
     - admin_records_actions.ts backfill logic in PRs #726/#727 can be removed once guard is in place
     
     ## Files expected to change
     - agent-service/src/agent-os/agents/_extract.ts (add validation)
     - agent-service/src/agent-os/agents/admin_records_actions.ts (remove backfill once guard ships)
     - agent-service/tests/_extract.test.ts (new unit tests)
     ```

## What This Replaces
Active direction: run 114 winner (Step 9K — implemented). This is a new direction addressing a recurrence pattern.

## Confidence
**HIGH** — 2 bugs same class in 2 days is strong pattern signal. Root cause clearly identified (_extract.ts, not admin_records_actions.ts). GH issue action (no direct code change) is risk-free today. Issue-to-pr-loop handles implementation when AUTOPILOT_GH_TOKEN is valid. Guard is bounded in scope (TypeScript validation function, no schema change, no new deps).

## Run 116 Mandate
1. Is the GH issue filed? Confirm issue number and ai-ready label.
2. os_tool_executions.py: stable (0 commits since 2026-08-30, now 3+ days)? If yes: run 116 god class split candidate.
3. Step 9K second run: how many open subconscious PRs? Any stale (>30d) or critical (>60d) changes?
4. GH #684 SUPABASE_ACCESS_TOKEN: set in Railway? Brain connector staleness resolved?
5. M8 OAuth/service_role HOLD: Calendar+CRM deploy progress?
6. Did issue-to-pr-loop open a draft PR for the new CRM guard GH issue?
