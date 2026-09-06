# Nightly Commit Review — 2026-09-06

**Period:** last 24 hours (from ~2026-09-05T02:30 UTC to 2026-09-06T02:30 UTC)
**Commits reviewed:** 9
**Issues filed:** 0
**Fixes applied:** 1 (LOW)

---

## Commit Triage

### 6c6cb36 — `test(website-connect): add migration-201 check-only staging preflight`
**Risk: LOW**
- Adds `scripts/website_connect_migration201_preflight.py` (223 lines) and `tests/test_website_connect_staging_readiness.py` (159 lines)
- Script is read-only preflight; refuses `--apply` and `APPLY_MIGRATION_201` env. Never mutates DB.
- Both files use `from __future__ import annotations` — acceptable: these are `scripts/` and `tests/` files, not FastAPI routers. CLAUDE.md Rule 5 applies to FastAPI files only.
- Migration 201 file confirmed to exist at `migrations/201_website_connections.sql`.
- No issues.

### a242c6e — `subconscious: run 115 — Step 9L AI metering coverage design (#795)`
**Risk: LOW**
- Pure planning/documentation files under `subconscious/runs/`. No code changes.
- No issues.

### 3a9a9e1 — `Merge pull request #791 from aferna6-cell/cursor/appointment-brief-guards-79ba`
**Risk: LOW**
- Merge commit only. Underlying changes reviewed via individual commits below.
- No issues.

### f5e78fe — `ci: include appointment brief tests in hosted coverage`
**Risk: LOW**
- Adds `test_appointment_brief.py`, `test_appointment_brief_budget.py`, `test_appointment_briefs_gating.py` to the CI pytest run.
- **BUG FOUND:** Missing EOF newline on last line of `.github/workflows/pr-check.yml`. Some CI/YAML parsers warn on this; cosmetic but non-compliant.
- **FIX APPLIED:** Added trailing newline.

### 92c5693 — `test: cover appointment budget denial and release`
**Risk: LOW**
- New `backend/tests/test_appointment_brief_budget.py` (145 lines).
- Tests appointment budget denial and release paths. Pure test additions; no production code touched.
- No issues.

### bd0ff02 — `test: cover usage-pack bonus in AI usage meter`
**Risk: LOW**
- Adds `test_ai_usage_status_includes_purchased_pack_bonus` to `backend/tests/test_os_kb_feed.py`.
- Tests that `_sum_usage_packs` bonus is included in `get_ai_usage_status` output (chatbot baseline 800k + 1M pack = 1.8M / 1000 = 1800 units).
- Uses `monkeypatch.setattr` cleanly. No `client_id`/`tenant_id` confusion.
- No issues.

### ad96e7a — `test: avoid secret-shaped literal in appointment budget regression`
**Risk: LOW**
- Splits `"sk-ant-test"` literal in test error string into `"sk" + "-ant-test"` to avoid pre-commit secret scanner false positive.
- Correct fix. No behavioral change.
- No issues.

### a5d2722 — `chore: integrate current main into appointment brief guards`
**Risk: LOW**
- Merge commit. No production changes.
- No issues.

### 51524d0 — `ops: nightly-commit-review 2026-09-05`
**Risk: LOW**
- Previous nightly review log commit. No code changes.
- No issues.

---

## Fixes Applied This Run

| Commit | File | Fix | Risk |
|--------|------|-----|------|
| (new) | `.github/workflows/pr-check.yml` | Added missing EOF newline on line 251 | LOW |

---

## CRITICAL RULES CHECK

- `client_id` not `tenant_id` on leads/conversations: No violations found in today's commits.
- `status` not `lead_stage`: No violations found.
- No `from __future__ import annotations` in FastAPI files: No violations. Usage confirmed only in `scripts/` and `tests/` files.
- Widget JS byte-identical: No widget changes today.
- Schema changes only via numbered migration files: No schema changes today.
- Secrets never in commits: `ad96e7a` explicitly fixes a secret-shaped literal — correct direction.

---

## Summary

All 9 commits are LOW risk. No MEDIUM or HIGH issues identified. One cosmetic bug fixed (missing EOF newline in CI YAML). No GitHub issues filed. Codebase healthy.
