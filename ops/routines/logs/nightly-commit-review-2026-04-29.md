# Nightly Commit Review — 2026-04-29

**Window:** last 24 hours (main)
**Commits reviewed:** 25
**Fixes applied:** 2 (both LOW)
**Issues filed:** 0

---

## Triage Summary

### LOW — Docs / config / scripts / tests (no action needed)

| SHA | Description |
|---|---|
| `964e8c7` | docs: schema-log.md update |
| `972e22d` | ops: architecture audit additions |
| `a1f74b9` | docs: schema-log.md update |
| `4d3aaad` | docs: opus47-prompting audit edits |
| `f52e3ca` | docs: audit + rule update |
| `3090278` | docs: PROMPTLIBRARY.md additions |
| `74cadd0` | docs: CLAUDE.md minor update |
| `d9b790a` | docs: fill-instructions-before-guessing.md |
| `08e18da` | docs: post-audit-remediation_plan.md |
| `f502172` | ops: morning-digest 2026-04-28 |
| `677b52c` | docs: bug-patterns.md auto-log |
| `dcc0f18` | frontend: capitalize homepage headline (cosmetic) |
| `1da09c2` | test: local_seo Phase 2 smoke tests |
| `10fad05` | test: local_seo handler tests |
| `e5c63ba` | test: fix import paths across test suite |
| `d73db8d` | scripts: check_plan_drift.py + tests |
| `7acb1ca` | scripts: pre-push hook + plan drift tests |
| `cd90932` | scripts: check_plan_drift.py initial |

### LOW — Bugs fixed by this review

#### Fix 1: Unused private imports in local_seo router (`2bb6982`)
- **File:** `backend/routers/local_seo.py`
- **Issue:** 3 private service functions (`_parse_json_array_response`, `_parse_json_object_response`, `_strip_json_fences`) imported into the router with zero usage in the router body. They belong only in service-layer callers (`local_seo_ai.py`, `local_seo_handlers.py`).
- **Fix:** Removed the 3 unused imports; `_verify_tenant` kept (used at 12 call sites).
- **Verified:** AST parse clean.

#### Fix 2: WizardStepAutoKB.jsx encoding corruption (`c289c2f`)
- **File:** `frontend/src/pages/wizard/WizardStepAutoKB.jsx`
- **Issue:** Commit `c289c2f` introduced a UTF-8 BOM and double-encoded all Unicode punctuation via cp1252 round-trip. 9 locations showed mojibake (`â€"`, `â€¦`, `â†`, `â†'`) instead of `—`, `…`, `←`, `→`. Visible to users on the onboarding auto-fill wizard step.
- **Fix:** Stripped BOM, replaced all 4 mojibake patterns with correct Unicode.
- **Verified:** Zero mojibake patterns remain (byte-level check passed).

### MEDIUM — Architecture / refactors (no new issues found)

| SHA | Description | Assessment |
|---|---|---|
| `2bb6982` | agent-system: routing guardrails; local_seo unused imports | Unused imports fixed above |
| `c289c2f` | agent-system: autopilot cleanup; skills trimmed | Encoding bug fixed above |
| `d60331e` | agent-system: skills hardened + classify_and_dispatch routing policy | Additive guardrail; clean |
| `e68677a` | fix(silent-errors): logging to 4 bare-exception handlers | Additive; fallback behavior unchanged |
| `8b638bd` | widget_chat.py: migrate imports from deleted barrel to sub-modules | Clean migration |
| `3405932` | widget_helpers.py deleted; tests already use direct imports | Clean; no orphaned callers |
| `a002e18` | refactor(local_seo) Phase 4: router 673→216 LOC | Structural; covered by tests |
| `f350f0e` | local_seo: Pydantic models extracted to models/local_seo.py | Clean extraction |
| `80f9815` | refactor(local_seo) Phase 2: handler extraction | Structural; covered by tests |
| `9187073` | local_seo: local_seo_ai.py + local_seo_scoring.py new services | Clean extraction |

### HIGH — Auth / payments / tenant isolation
None in this window.

---

## CLAUDE.md Critical Rule check

- `client_id` not `tenant_id` on leads/conversations: no violations found
- `status` not `lead_stage`: no violations found
- No `from __future__ import annotations` in FastAPI files: none found
- Secrets in commits: none detected
- Widget byte-identity: no widget JS changes in this window

All critical rules pass.

---

## Files changed by this review

- `backend/routers/local_seo.py` — removed 3 unused private imports
- `frontend/src/pages/wizard/WizardStepAutoKB.jsx` — fixed encoding corruption (9 locations)
- `ops/routines/logs/nightly-commit-review-2026-04-29.md` — this file
