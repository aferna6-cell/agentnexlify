### Idea 5: Wire check_schema_log_drift.py into CI

**Evidence:**
Commit 43844a5 (2026-09-05, merged today): "feat(schema): read-only schema-log vs live migration
drift guard." Nightly classified it LOW — standalone script, no FastAPI file, no wiring to CI.
The script catches schema-log vs actual migration divergence. bug-patterns.md lists client_id/tenant_id
mixup as the #1 recurring bug class (3+ production bugs). Schema invariants are the most duplicated
critical rule in CLAUDE.md (items 1-3). A drift guard that's only run manually provides zero
protection — attackers work every commit, guards must run every commit.

**Action:**
Add `python scripts/check_schema_log_drift.py --check` step to `.github/workflows/pr-check.yml`
as a new CI job (after existing checks). Add to `scripts/pre-push` as a warning-only Check 10.
Zero new dependencies — script reads migration files + schema-log.md already present.

**Impact:**
Every PR validates migration log vs codebase. Zero unreported schema drift.
Same class as check_project_invariants.py — preventive enforcement.
Category: code_health
Effort: S (add CI step + pre-push line)
Note: Lower urgency than Step 9L because billing leaks are currently bleeding (13 unguarded routes
confirmed), while schema drift guard prevents future bugs rather than closing active bleeding.
