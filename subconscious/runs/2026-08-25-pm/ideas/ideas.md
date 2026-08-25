# Run 111 Ideas — 2026-08-25-pm

## Evidence Summary

- **Revenue sprint 10acf83** (today, 46 files, 2866 lines): added `backend/routers/partners.py` and `backend/routers/billing_addons.py`. Direct grep confirms `partners.py` has NO `block_demo_role`. `billing_addons.py` has it correctly at lines 22/35.
- **Step 9J: 0 merges** — GH Actions dark since 2026-07-20 (GH #500). All Dependabot PRs have `mergeable_state: "unknown"` because required CI checks can't run. Step 9J is structurally blocked.
- **Step 9I dynamic scan** — correctly scans all router files via grep. Will catch `partners.py` on next nightly (2026-08-26). Dedup check for "partners.py block_demo_role" in open issues will return 0 hits → new issue will be filed. No SKILL.md change needed for this specific file.
- **GH #669**: 97 routers missing block_demo_role. Pattern recurring — each sprint adds new routers. Detection (Step 9I, nightly) is reactive; no preventive mechanism at commit time.
- **10acf83 tests**: test_partners_inquiry.py (94 lines), test_billing_annual.py (386 lines), test_churn_watch_call_list.py (228 lines), test_voice_addon.py (248 lines) — coverage looks adequate per file counts.
- **Run 110 AM winner** (already in PR #683): Step 9K stale PR closer. Already weakened in that run: block_demo_role middleware (PR #653), memory.jsonl dedup guard.

---

## Idea 1 — Pre-commit block_demo_role detection hook

**Category:** security  
**Effort:** M  
**Channel:** human-approve-implement

Add `scripts/claude-hooks/check-router-guards.sh` — a pre-commit hook that:
1. Identifies staged Python files in `backend/routers/`
2. Checks if they contain `@router.post/put/delete/patch`
3. If yes, checks for `block_demo_role` import + usage
4. If absent: emits WARNING with fix pattern (non-blocking — doesn't prevent commit)

Register in `scripts/install-hooks.sh` as a pre-commit step (alongside existing secrets scan, `__future__` check, bare-except).

**Evidence:** partners.py was committed today in 10acf83 WITHOUT block_demo_role. billing_addons.py in the same sprint HAS it. A pre-commit warning would have flagged partners.py at commit time, not the next nightly.

**Impact:** Shifts detection from nightly (12-36h lag) to commit (immediate). Stops future GH #669-class security gaps at source. GH #669 has 97 accumulated violations — this prevents the 98th+.

---

## Idea 2 — Step 9J: consecutive-0-merge escalation to GH issue

**Category:** operational  
**Effort:** S  
**Channel:** autonomous-executable (SKILL.md edit)

Update Step 9J in nightly-commit-review SKILL.md:
- Add tracking: if all minor/patch candidates have `mergeable_state: "unknown"` for ≥3 consecutive nights → check if a GH issue exists with title containing "Dependabot auto-merge blocked"
- If no issue: file one via `mcp__github__issue_write` referencing GH #500 and listing the aging PRs by number

**Evidence:** Step 9J has been 0-merge every night since implemented (first run 2026-08-25). Root cause: GH Actions dark → no CI runs → `mergeable_state` never reaches "clean". Aging Dependabot PRs (#629/#630/#631 are 22d old). No tracking issue exists for this specific blocker.

**Impact:** Converts a silent operational dead-end into a tracked, escalated issue. Ensures the human who restores GH Actions (#500) knows there are aging Dependabot PRs waiting.

---

## Idea 3 — Annual plan guard consistency check (one-time audit)

**Category:** code_health  
**Effort:** XS  
**Channel:** human-approve-implement

10acf83 added annual billing plans (from `test_billing_annual.py`: 386 lines of tests for annual prepay logic). Check that:
1. `ai_usage_guard.py` PLAN_BASELINE_TOKENS includes annual plan variants (e.g. `agent_os_annual`, `chatbot_annual`) OR that annual plans map to existing plan names in the guard
2. `stripe_service.py` annual price IDs are consistent with plan gating in `backend/services/stripe_service.py`
3. New annual plan tenants won't be classified as `free` by the usage guard

**Evidence:** 10acf83 changed stripe_service.py and billing.py significantly. The usage guard gates AI token spend by plan name. If the annual plan's Stripe price ID returns a plan_name not in PLAN_BASELINE_TOKENS, annual subscribers get free-tier token limits.

**Impact:** Prevents revenue-eroding misclassification of paying annual-plan subscribers as free-tier users.

---

## Idea 4 — Step 9J: lower merge threshold when GH Actions confirmed dark

**Category:** operational  
**Effort:** M  
**Channel:** human-approve-implement (requires policy decision)

Update Step 9J to accept `mergeable_state: "blocked"` (no conflicts, but required checks pending) as merge-eligible ONLY when GH Actions has been confirmed dark (check GH #500 open state) AND the Dependabot PR is patch-only (no minor version bump). This would unblock the 22-day-old Dependabot PRs.

**Evidence:** `#629 @playwright/test 1.61.1→1.62.1` (patch), `#630 vite 8.1.5→8.2.0` (minor — borderline), `#631 @vitejs/plugin-react 6.0.3→6.0.5` (patch). Patch bumps with no conflicts are safe to merge even without CI.

**Impact:** Unblocks 2-3 aging Dependabot PRs immediately, shrinks security window.

**Risk:** MEDIUM — merging without CI passing is policy-level. Not autonomous-executable without human approval.

---

## Idea 5 — Nightly Step 9D: detect stale issue-to-PR-loop differently when GH Actions dark

**Category:** operational  
**Effort:** S  
**Channel:** autonomous-executable (SKILL.md edit)

Step 9D currently checks `autopilot-issue-loop.yml` disabled status and reports "GH Actions dark since 2026-07-20 (GH #500) — autopilot-issue-loop.yml disabled per fix(ci) commits. Loop runs via Routines instead." But it doesn't check HOW LONG GH Actions has been dark or escalate after a threshold.

Update Step 9D: if GH Actions dark for >30 days (check last workflow run date) AND no GH issue exists tracking restoration → file escalation issue titled "[ops] GH Actions dark 30+ days: restore to unblock Dependabot auto-merge, KB autopopulate, autopilot loop".

**Evidence:** GH Actions dark since 2026-07-20 — today is 2026-08-25, that's 36 days. Multiple downstream blockers: Step 9J (0 Dependabot merges), Step 9G (KB autopopulate dead), Step 9D (autopilot loop stalled). GH #500 is open but may not surface the cascading impact.

**Impact:** Creates an escalation issue that quantifies the total cascading cost of GH Actions being dark. Gives the human a single actionable ticket with the full blast radius documented.
