# Ideation — Run 52 (2026-06-07)

## Evidence Digest

**Recent commits (3 days):**
- `7a621a1` — Agent OS engine adopted as orchestration core (7,640 insertions, 96 files, migration 131 adds os_routing_decision + os_model_call_log tables)
- `abccdc3` — Agent-service auth hardened before v2 activation (X-Agent-Token header check, 25 tests)
- `2287f6b` — Fix: Agent OS no longer hijacks public widget (widget_enabled default → False, regression test added)
- `fff7193` — Nightly review filed GH #206 (timing-safe comparison missing in auth.ts)

**Critical findings this run:**
- `nightly-commit-review SKILL.md:69` has stale blocker: "Blocked 2026-06-01: script fails on em-dash violations in UI copy." Em-dash was fixed by `8db33df` on 2026-06-05. This stale note is why Item A (Check 10) has NOT fired in 2 nightly cycles despite pre-condition being met.
- No Item B block in SKILL.md. PR #200 (run 50 scope extension) was not merged before nightlies ran.
- `billing.py:263` AMOUNT_TO_PLAN still missing 15000+25000. PR #183 not merged. GH #181 day 52+.
- `email_sequences.py` still 1255L. GH #181 prerequisite unresolved.
- `auth.ts:14` uses `===` for token comparison (GH #206, filed today). Railway private network reduces current exposure.
- Moratorium day 37. 15 pending (governance). True human-required: ~6.

---

### Idea 1: Remove Stale Item A Blocker from nightly-commit-review SKILL.md:69
**Evidence:** SKILL.md:69 says "Blocked 2026-06-01: script fails on em-dash violations in UI copy." This note is factually wrong — `8db33df` (2026-06-05) fixed all 5 em-dash violations. `check_project_invariants.py` confirmed exit 0 in run 50. Two nightly cycles since then applied 0 autonomous items because the nightly reads "Execute when script passes clean" as conditional on the blocker being absent. Stale note = gate stuck closed.
**Action:** Human edits SKILL.md:69 to remove the stale sentence "Blocked 2026-06-01: script fails on em-dash violations in UI copy." (1-line deletion, ~1 min). Nightly next cycle reads Item A as unblocked, runs pre-condition check, applies Check 10 patch, commits.
**Impact:** Unblocks Check 10 (pre-commit check_project_invariants guard) after 46-day wait. Fires autonomously at 2:37 AM tonight. Zero human coding required after the 1-line SKILL.md edit.
**Category:** workflow / code_health

---

### Idea 2: Fix auth.ts Timing-Safe Token Comparison (GH #206)
**Evidence:** `auth.ts:14` — `return value === expected`. GH #206 filed today by nightly review. Agent OS engine (7a621a1) expands agent-service to 20+ endpoints with auth gate. Railway private networking reduces current exposure but doesn't eliminate it. Nightly assessment: "requires human approval."
**Action:** Edit `agent-service/src/auth.ts` — replace `return value === expected` with constant-time comparison using Node.js `crypto.timingSafeEqual(Buffer.from(value ?? ''), Buffer.from(expected))` with null/length guards. Add/update test to verify rejected tokens with different lengths.
**Impact:** Closes GH #206. Hardens auth before v2 engine activation. Prevents timing oracle if agent-service ever routes through a public edge.
**Category:** code_health / security

---

### Idea 3: Add Item B Block to nightly-commit-review SKILL.md
**Evidence:** `scripts/check-widget-sync.sh` MISSING for 43+ days. Run 50 winner was AUTONOMOUS-EXECUTABLE for Item B but the SKILL.md block was never added (PR #200 not merged). The nightly can't execute what isn't in its playbook. Three-copy widget sync risk (widget/, frontend/public/widget/, landing-page-v2/widget/) is a CLAUDE.md Critical Rule #4 that has no automated enforcement.
**Action:** Human adds Item B block to nightly-commit-review SKILL.md with full script content + pre-push hook patch (from run 50 winning-concept.md). Nightly creates `scripts/check-widget-sync.sh` + wires into `scripts/hooks/pre-push` + fixes CLAUDE.md Invariant #4 on next cycle.
**Impact:** Closes 43-day widget sync guard gap. Prevents byte-identical invariant violation from going undetected. Autonomous execution.
**Category:** code_health / workflow

---

### Idea 4: Merge PR #183 (GH #181 Billing Fix)
**Evidence:** AMOUNT_TO_PLAN confirmed missing 15000 (autopilot $150/mo) + 25000 (professional $250/mo) via live check (billing.py:263). Run 51 winner same recommendation. GH #181 day 52+. email_sequences.py split blocked pending this.
**Action:** Human reviews PR #183 diff (verify targets backend/routers/billing.py not services/), confirms CI status, merges.
**Impact:** Closes GH #181. Silences Check 11 WARNING. Unblocks email_sequences.py split (run 41, 1255L). Direct revenue integrity improvement.
**Category:** code_health

---

### Idea 5: Confirm Migration 131 Applied to Production
**Evidence:** `7a621a1` adds migration 131 (os_routing_decision + os_model_call_log tables). Nightly review noted: "migration 131 must be applied to production Supabase if not already done." No confirmation in any commit or log that it was applied. Agent OS engine activates when AGENT_SERVICE_URL is set — if that env var is live, backend queries against migration 131 tables that don't exist → 500 errors.
**Action:** Open GH issue with label `ops + critical`: "Verify migration 131 applied in production Supabase for Agent OS engine tables." Include MCP apply command. Route to issue-to-pr-loop.
**Category:** operational
