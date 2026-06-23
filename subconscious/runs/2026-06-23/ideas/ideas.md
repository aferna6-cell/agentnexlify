# Candidate Ideas — Run 65 (2026-06-23)

## Idea 1: Add plan-name guard Check 7 to check_project_invariants.py

**Evidence:** GH #292/#293 fixed by `29ed1d4`/`57f2bb4`/`c461cef` (2026-06-21). plan_catalog.py created (3d4c7db) with CURRENT_PAID_PLANS = frozenset({"chatbot","agent_os"}). This item was explicitly queued as "Bonus B, AUTONOMOUS-EXECUTABLE" in runs 59-64, gated on GH #292/#293. Four prior incidents from repricing gate drift (GH #81, #181, #292, #293).

**Action:** Add ~10-line python block to check_project_invariants.py: import plan_catalog.CURRENT_PAID_PLANS; for each plan-gate dict/set in sms_rate_limiter._UNLIMITED_PLANS, api_key_auth._ALLOWED_PLANS, billing_reconciliation caps, verify all CURRENT_PAID_PLANS are present. FAIL (non-zero exit) if any are missing.

**Impact:** Prevents 5th repricing-triggered gate drift incident. Any future `CURRENT_PAID_PLANS` change automatically guards all downstream gate dicts at commit time.

**Category:** code_health

---

## Idea 2: Review and merge PR #209 (timing-safe token comparison, agent-service auth.ts)

**Evidence:** PR audit 2026-06-22 explicitly flagged: "Note: #209 (timing-safe token comparison) may be a real security fix — review before closing." GH #206 documented timing attack in agent-service/src/auth.ts. Run 52 Check 12 added pre-commit WARNING but not a code fix.

**Action:** Read PR #209 diff. If it patches agent-service/src/auth.ts (=== on X-Agent-Token → timingSafeEqual), merge before the stale-draft cleanup closes it.

**Impact:** Closes live timing-attack window on tenant agent authentication.

**Category:** code_health / security

---

## Idea 3: AI-to-Human Handoff v1 (explicit trigger, run 4, 68 days)

**Evidence:** customer-gaps.md: Critical, all 7 industries. os_outbound_mirror.py (PR #188, 152 tests) provides delivery layer. Run 38 scoped ~1 day. Mandate bottleneck (GH #292/#293 + #308) both now resolved — first cycle without an alternating mandate.

**Action:** widget_chat.py: detect explicit trigger phrases ("talk to someone", "human", "person"). Set lead.status = "needs_follow_up". Call os_outbound_mirror.send_sms or send_email to owner. Return soft handoff message to customer.

**Impact:** Converts #1 cross-industry gap. Closes 68-day run 4 item.

**Category:** customer_value

---

## Idea 4: Merge Batch A + D Dependency PRs (#342, #281, #279, #277, #340, #273, #15, #14, #13, #12, #11)

**Evidence:** PR audit 2026-06-22 documented 48 open PRs. Batch A (6 dev-dep patches: vitest, @typescript-eslint, @playwright) and Batch D (5 GitHub Actions bumps) are classified MERGE-SAFE once CI green. PR #348 (CI minute budget) merged — CI now green.

**Action:** Batch merge A+D in single PR/commit series. Batch B (runtime deps) follows with smoke test.

**Impact:** Clears 11+ stale PRs from the backlog in one pass. Keeps toolchain current without manual triage.

**Category:** operational

---

## Idea 5: Deterministic migration object-existence audit (kill GH #263 false-alarm class)

**Evidence:** migration-triage-2026-06-22.md confirmed GH #263 ("24 pending migrations") is a false positive from number-based diff. Triage explicitly recommended: "parse CREATE TABLE / ADD COLUMN targets and check against information_schema — this kills the recurring #263 false alarm." Numeric diffs will continue firing indefinitely without this.

**Action:** Create scripts/check_migration_objects.py: for each migrations/NNN_*.sql, parse DDL targets (CREATE TABLE, ADD COLUMN, CREATE INDEX, CREATE FUNCTION) and query information_schema to confirm existence. Output: confirmed-missing vs applied-under-different-name vs truly-pending. Add as optional check_project_invariants.py extension or standalone script.

**Impact:** Eliminates recurring false-alarm class. Future migration reviews take minutes not hours.

**Category:** operational / code_health
