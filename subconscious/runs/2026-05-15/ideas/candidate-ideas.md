# Candidate Ideas — Run 17 (2026-05-15)

## Evidence Digest

Zero implementation velocity in 4 days since run 16. Three nightly review commits (May 13-15) are the only activity — pure logging, no code. All three S-effort pending items unimplemented: `scripts/check-widget-sync.sh` MISSING (run 7, day 21), `check_project_invariants.py` not wired (run 8, day 20), `lead-qualifier-eval.yml` MISSING (run 14, day 10). Widget copies confirmed IN SYNC (May 15 nightly PASS) — good state, but guard preventing future drift still absent. AI-to-Human Handoff (run 4) now 29 days old — most overdue pending item. Moratorium still active: pending_approvals=4 > threshold=3. Widget 3-Copy Sync Guard has been moratorium winner across runs 15 and 16; run 16 explicitly flagged: "If run 17 has same winner, consider Automated Moratorium Escalation Hook as meta-fix." Zapier issue #107 now 15 days open (was 11 in run 16) — security gap growing. bug-patterns.md unchanged at 2379 lines. KB stable at 114 articles.

---

### Idea 1: Widget 3-Copy Sync Guard (moratorium mandate, run 7 re-escalation)
**Evidence:** `scripts/check-widget-sync.sh` confirmed MISSING (May 15). Widget copies are in sync today but no automated guard prevents future drift. Moratorium active: pending=4 > threshold=3. Run 7 (April 24) = day 21. Oldest S-effort pending. JS Silent Catch precedent: recommended across 6 consecutive moratorium runs (9-13) before being implemented. Moratorium protocol mandates oldest S-effort pending as winner.
**Action:** Create `scripts/check-widget-sync.sh` (implementation sketch unchanged from run 15/16), wire into `scripts/hooks/pre-push`, fix CLAUDE.md Invariant #4 (2 → 3 widget paths). S-effort ~15 min.
**Impact:** Prevents widget copy drift before it happens. Drops pending 4→3 on approval. Bonus A+B drops pending to 1 in a single 45-min sitting.
**Category:** code_health

---

### Idea 2: Automated Moratorium Escalation Hook (meta-improvement, parking lot)
**Evidence:** Run 16 explicitly flagged: "If run 17 has same winner again, consider adding Automated moratorium escalation hook as meta-fix." 3 consecutive runs (15, 16, 17 if same winner) with identical recommendation and zero implementation. nightly-commit-review.sh runs every night but has no mechanism to create GH pressure on oldest pending issues. GH issues are where humans spend implementation time.
**Action:** Modify `scripts/daily/nightly-commit-review.sh` to auto-create a GH comment on the oldest pending issue (linking `winning-concept.md`) when moratorium is active AND oldest_pending > 14 days. Requires mcp__github__add_issue_comment or gh CLI. S-effort ~1 hour.
**Impact:** Creates automated human-facing pressure in GitHub (where implementation happens), not just in subconscious artifacts. Closes the recommendation→implementation feedback gap. Would have surfaced run 7's Widget Sync Guard on run 4's GH issue 7 days ago.
**Category:** workflow

---

### Idea 3: Zapier API key plan_status enforcement (security, issue #107)
**Evidence:** `backend/services/zapier_auth.py::_get_api_key_client` resolves keys without checking `tenants.plan_status`. Cancelled tenants with un-revoked keys bypass tier gate. bug-patterns.md entry confirmed. GH issue #107 now 15 days open (was 11 in run 16). ROI 2.5. HIGH security.
**Action:** Add `plan_status IN ('active','trialing')` filter inside `_get_api_key_client`. Add regression test seeding cancelled tenant + valid key + asserting 402/403. Route via issue-to-pr-loop, NOT subconscious queue.
**Impact:** Closes tier-gate bypass for cancelled tenants. Prevents revenue leakage from expired subscriptions. Regression test prevents re-introduction.
**Category:** code_health / security

---

### Idea 4: Wire check_project_invariants.py into pre-commit hook (run 8, S-effort bonus)
**Evidence:** Run 8 winner (April 25, day 20). `scripts/check_project_invariants.py` passes all 6 checks (confirmed). Not wired into `scripts/hooks/pre-commit`. Pre-commit has 9 checks; this is Check 10. 8-line addition. Zero blockers since em-dash cleared (8f680e8). S-effort ~5 min.
**Action:** Add 8-line block after existing Check 9 in `scripts/hooks/pre-commit`. No new dependencies.
**Impact:** Automated blocking of `tenant_id`, `lead_stage`, `service_interest` naming violations at commit time. Drops pending 4→3. Combined with run 7 drops pending 4→2.
**Category:** code_health

---

### Idea 5: Bug-patterns.md split by month (parking lot, tech hygiene)
**Evidence:** bug-patterns.md at 2379 lines (unchanged from run 16). Auto-logger writes to it at root. File has grown 175 lines since run 7 (April 24). No month-based index exists. Long file slows grep-based debugging lookups and violates tiered retrieval discipline.
**Action:** Split `docs/dev-knowledge/bug-patterns.md` into `docs/dev-knowledge/bug-patterns/YYYY-MM.md` monthly files + `INDEX.md`. Update `scripts/daily/nightly-commit-review.sh` auto-logger path to write to current month.
**Impact:** 6-12x grep performance for bug lookup (per memory-tiered-retrieval rule). Reduces per-query token cost in debugging sessions. Makes auto-logger output more structured.
**Category:** code_health / workflow
