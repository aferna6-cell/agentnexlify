# Codebase Debug Audit — 2026-04-15

**Method:** systematic-debugging skill (4-phase: reproduce → narrow → diagnose → verify) applied across full backend + frontend + widget.
**Scope:** All antipatterns documented in `CLAUDE.md` Critical Invariants + standard quality checks.
**Outcome:** **0 active bugs.** 2 quality-debt findings, 1 organizational suggestion.

## Phase 1 — Reproduction setup

Local tooling status:
- Python 3.14.2 — works
- Node v24.14.1 — broken locally (`npm` missing `nopt` module). Frontend build/lint not executable from this session.
- Backend test runner unavailable (no `.env` in session, security rules block reading credentials).

Therefore audit is **static-analysis only**. Runtime test verification deferred to CI / next live session with env.

## Phase 2 — Narrowing (parallel scans)

### Antipattern checklist per CLAUDE.md
| # | Antipattern | Result | Notes |
|---|---|---|---|
| 1 | `from __future__ import annotations` in FastAPI files | ✅ CLEAN | Only mention is in `backend/CONTEXT.md` (rule documentation) |
| 2 | `tenant_id` column on leads/conversations queries | ✅ CLEAN | All `.eq("client_id", ...)` confirmed; `tenant_id` only as variable name (correctly holds the client_id value) |
| 3 | `lead_stage` column references | ✅ CLEAN | Only in `_archive/`, audit docs, rule files, GH workflow linters |
| 4 | `service_interest` column references | ✅ CLEAN | Same as above |
| 5 | Widget JS byte-mismatch | ✅ CLEAN | `widget/agentnexlify-widget.js` and `frontend/public/widget/agentnexlify-widget.js` both 65993 bytes, `diff` empty |
| 6 | `localStorage` in React artifacts | ✅ CLEAN | 12 hits in `frontend/src/` are normal browser code, NOT artifact context |
| 7 | Bare `except:` blocks in backend | ✅ CLEAN | 0 matches |
| 8 | Hardcoded retired plan names (`foundation`, `operations`) | ✅ CLEAN | 0 matches in backend |
| 9 | Leaked secrets (`sk_live_`, `whsec_`, AWS keys, PEM) | ✅ CLEAN | 1 hit in `resend_webhooks.py` is legitimate signature parsing |
| 10 | Backend Python syntax/import errors | ✅ CLEAN | Full `python -m compileall` + AST parse: 0 broken files across entire `backend/` tree |
| 11 | `console.log`, `debugger` statements | ✅ CLEAN | 0 hits in non-test frontend code |
| 12 | Unwired routers in `backend/main.py` | ✅ CLEAN | 65/67 router files wired; 2 unwired files (`widget_booking.py`, `widget_helpers.py`) are HELPERS without `router =` declaration — correctly not-wired |

### Tooling that could not run
- `npm run build` — npm broken locally
- `npm run lint` — npm broken locally
- `pytest backend/tests/` — env vars missing
- `pip-audit` — not installed in session
- `gitnexus_query` — index status not verified

## Phase 3 — Diagnosis (findings)

### F1 — UX debt: 27 native `alert()` calls in dashboard pages
**Severity:** MEDIUM (UX, not functional bug)
**Files:** ABTestsPage, AdminPromotionsPage, AutomationRulesPage, BillingPage, BusinessPageSettings, ContentRepurposePage, EmailSequencesPage, InvoicesPage, MarketingCampaignsPage, PipelineAutomationsPage, SettingsPage, SocialMediaPage
**Pattern:** all are error-message displays after API failure (`alert(err.message || "Failed to ...")`)
**Impact:** native browser `alert()` blocks UI thread, looks unprofessional, inconsistent with dashboard's dark-theme design system
**Recommended fix:** replace with toast/notification component (single shared util)
**Why not fixed in this session:** 12 files × multiple call sites = scope too large for in-session "additive" fix per Rule 11. Needs decision on toast library + designed UX. → File GH issue.

### F2 — Organizational debt: helper modules in routers/ folder
**Severity:** LOW (naming/discoverability)
**Files:** `backend/routers/widget_booking.py` (460 lines), `backend/routers/widget_helpers.py`
**Issue:** neither file declares `router = APIRouter()`. Both are imported as helpers by `widget_chat.py`, `widget_config.py`, `widget_lead.py`, `auth.py`, `twilio_webhooks.py`.
**Detection cost:** confused my router-wiring audit (false positive). Future devs/agents doing `ls backend/routers/` will expect routers.
**Recommended fix:** move to `backend/services/widget/` (one PR, update 5 import sites)
**Why not fixed in this session:** crosses 7 files, would invoke pre-push hook + risk import-graph changes. Better as scoped PR with test verification.

### F3 — Local tooling regression (env, not code)
**Severity:** LOW (developer experience, env-only)
**Issue:** `npm` on host can't load `@npmcli/config` due to missing `nopt`. Likely Node 24 / npm version mismatch.
**Impact:** can't run frontend build/lint/tests from this Windows host without npm reinstall.
**Recommended fix:** `npm install -g npm@latest` or use Node 22 LTS via `nvm`. Not a repo issue.

## Phase 4 — Verification

What was VERIFIED clean:
- Python compiles (full backend/)
- Python AST parses (full backend/)
- All routers wired
- All schema invariants honored
- Widget byte-sync intact
- No leaked credentials
- No deferred-annotation FastAPI footgun
- No bare exception swallowing

What requires CI / next live session:
- `pytest backend/tests/` (needs env)
- `npm run build` (needs working npm)
- `npm run test` (needs working npm)
- pip-audit / npm audit (needs working tooling)

## Producer skills used
- `systematic-debugging` — 4-phase methodology
- `triage-issue` — structured diagnosis
- `dependency-auditor` — partial (couldn't run pip-audit / npm audit)
- `security-audit` — partial (couldn't run automated tools)

## Recommended follow-ups (file as `ai-ready` GH issues)
1. **F1 → issue:** "Replace 27 native `alert()` calls with toast component" — `layer/frontend, priority/p2, ai-ready`
2. **F2 → issue:** "Move widget helpers out of `backend/routers/`" — `layer/backend, priority/p3, ai-ready`
3. **F3:** developer doc note — add troubleshooting line to `frontend/CONTEXT.md` re: Node 22 LTS
4. **CI gap:** verify health-check.yml runs the antipattern scans this audit ran (it does, per `.github/workflows/health-check.yml` lines 86-89)

## Confidence in audit completeness
- Static checks: 95% — covered all CLAUDE.md invariants
- Runtime correctness: ~30% — could not execute build/test/audit tools
- Net audit confidence: 80% — strong on patterns, weak on runtime

## Audit method (for re-running)
```bash
# Antipattern scans (all run in parallel)
grep -rn "from __future__ import annotations" backend/
grep -rn "lead_stage\|service_interest" backend/ --include="*.py" | grep -v _archive
grep -rn "^\s*except\s*:" backend/
diff -q widget/agentnexlify-widget.js frontend/public/widget/agentnexlify-widget.js
python -m compileall -q backend/
python -c "import ast,os; [ast.parse(open(os.path.join(r,f),encoding='utf-8').read()) for r,_,fs in os.walk('backend') for f in fs if f.endswith('.py') and '_archive' not in r]"

# Router wiring audit (see audit body for full Python)

# Quality scans
grep -rn "^\s*alert(" frontend/src/ --include="*.jsx"
grep -rn "console\.log\|debugger" frontend/src/ --include="*.jsx" | grep -v test
```

Run quarterly, after major refactors, before any release.
