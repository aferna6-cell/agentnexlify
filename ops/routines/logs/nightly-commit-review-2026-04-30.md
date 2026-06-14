# Nightly Commit Review — 2026-04-30

**Window:** last 24 hours (main)
**Commits reviewed:** 17
**Fixes applied:** 1 (LOW)
**Issues filed:** 1 (MEDIUM — #107)

---

## Triage Summary

### LOW — Docs / KB / config / logs (no action needed)

| SHA | Description |
|---|---|
| `930c08a` | kb(log): append run summary 2026-04-29 18:19 |
| `d1150e1` | chore(ai): auto-commit KB articles (3 new) |
| `c2b2a85` | chore(ai): auto-commit KB articles (3 new wiki pages) |
| `0f2f075` | docs(plan): mark ops-automation Phase 1 DONE |
| `d6e4ae6` | plan(marketing-addon): activation + UX audit + CSV workstreams |
| `78e590f` | docs(kb): realtime-voice + NotebookLM + kb-ingest spike |
| `0f5e47b` | chore(ai): skills + settings + agent-routing-eval.json updates |
| `151584f` | kb(log): append run summary |
| `0489065` | chore(ai): KB articles (feature/58-zapier-auth branch) |
| `c77a80e` | chore(ai): KB competitor article (ghl-voice-ai-review) |
| `757444d` | docs: automated morning startup 2026-04-29 |
| `3184840` | fix(nightly-review): LOW bugs from prior run (committed by this agent) |
| `1cd157b` | fix(nightly-review): prior run fixes (prior agent) |
| `9db6944` | ops: nightly-commit-review 2026-04-29 (log commit) |

### LOW — Bug fixed by this review

#### Fix 1: Reasoning-trace comment noise in `_mask_phone` (`activity.py`)

- **SHA causing it:** `f4b8166` (feat(attribution): extend get_activity_totals)
- **File:** `backend/services/activity.py:28-46`
- **Issue:** 11-line reasoning-trace comment block left inside `_mask_phone` showing developer confusion about the masking spec, containing contradictory statements ("But spec wants... Recount:... Actually spec says..."). Future readers would need to re-derive the algorithm from the noise.
- **Fix:** Replaced with a single accurate description: `# Show first max(len-8, 4) digits + **** + last 4 (min 9 digits to avoid overlap)`
- **Verified:** `python3 -c "import ast; ast.parse(...)"` → AST OK. Behavior unchanged.

### MEDIUM — New features reviewed

#### `f54dc7e` + `f4b8166` — Attribution service (slice 1 + 2)

- **Files:** `backend/services/attribution_service.py`, `backend/services/activity.py`, `config/vertical_defaults.yaml`, `config/hours_saved_formula.yaml`
- **Assessment:** Clean new service. Uses `Decimal` throughout (money invariant respected). YAML configs via `lru_cache` (one load per process). No schema column violations (`tenant_id` on `activity_log` is correct — that table uses `tenant_id`, not `client_id`). Error isolation per-call in `get_activity_totals` so `events_count` returns even when attribution fails. 16 tests pass.
- **Risk:** LOW-MEDIUM. Pure additive, no existing code modified.

### HIGH — Auth / tier-gated features

#### `eed7794` — Merge feature/58-zapier-auth: tier-gated Zapier API key auth

- **Files:** `backend/routers/zapier.py`, `backend/services/api_key_auth.py`, `backend/services/api_key_limiter.py`
- **Assessment:** Auth implementation quality is good — bcrypt cost 12, prefix-indexed lookup, `secrets.token_urlsafe(32)`, revoked_at soft-delete, ownership check before revoke. Schema discipline: `client_id` used correctly throughout. `areas_of_interest`/`status` used correctly in leads query. No `__future__` annotations. 584-line test suite.
- **MEDIUM issue found:** `plan_status` not enforced in `_get_api_key_client`. Cancelled/past_due tenants with a paid plan bypass tier gating. Filed as **GitHub Issue #107**.
- **Rate limiter:** In-memory per-worker (4x effective RPM). User-approved as Redis substitute (documented in service file). Not a bug.

#### `23f15cc` — Merge fix/81-billing-verify

- **Files:** `backend/tests/test_billing_amount_to_plan.py` (new, 96 lines)
- **Assessment:** Defensive test addition. Bug was not present; tests now prove it. LOW risk, additive.

#### `4540b39` — Merge fix/82-scheduled-jobs

- **Assessment:** Documentation of existing import chain. No code changes. LOW.

---

## CLAUDE.md Critical Rule check

- `client_id` not `tenant_id` on leads/conversations: **PASS** — zapier.py leads query uses `client_id` correctly; `activity_log` correctly uses `tenant_id`
- `status` not `lead_stage`: **PASS** — `LeadRow.status` correct
- `areas_of_interest` not `service_interest`: **PASS** — correct in `LeadRow`
- No `from __future__ import annotations` in FastAPI files: **PASS** — checked all new files
- Secrets in commits: **PASS** — none detected
- Widget byte-identity: N/A — no widget JS changes this window

All critical rules pass.

---

## Issues filed

| # | Title | Risk | Labels |
|---|---|---|---|
| [#107](https://github.com/aferna6-cell/agentnexlify/issues/107) | fix(zapier): enforce plan_status check in _get_api_key_client | MEDIUM | nightly-review, medium, backend |

---

## Files changed by this review

- `backend/services/activity.py` — comment cleanup in `_mask_phone` (behavior unchanged)
- `ops/routines/logs/nightly-commit-review-2026-04-30.md` — this file
