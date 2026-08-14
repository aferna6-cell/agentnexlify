# Run 106 — Debate Log (2026-08-14)

## Top 3 (Idea 1, Idea 2, Idea 3)

---

### Round 1: Idea 1 vs Idea 2

**Idea 1 (appointment_briefs.py fix):**
- STRENGTHENED: GH #643 is 7d open, labeled ai-ready+security. Run 105 explicitly cleared AUTONOMOUS-EXECUTABLE. Nightly infrastructure constraint (operates on main) proves standard channel cannot deliver.
- STRENGTHENED: Exact implementation known — billing.py:33 canonical, route-security-guard-audit SKILL.md exists. 10-min fix.
- STRENGTHENED: Demo tenants currently have unguarded access to AI-generated appointment briefs and follow-up drafts. Every day without the fix is an active security gap.

**Idea 2 (pr-backlog-triage SKILL.md):**
- WEAKENED: The tool it would automate (AUTOPILOT_GH_TOKEN) is expired. A triage skill that can't run is less valuable.
- WEAKENED: The PR pile it would address (4 dependabot + 1 subconscious) is manageable manually. No acute pain signal.
- SURVIVES as parking lot — good idea once #399 resolved.

**Winner of Round 1: Idea 1**

---

### Round 2: Idea 1 vs Idea 3

**Idea 1 (appointment_briefs.py fix):**
- HOLDS: Primary security gap. Demonstrates autonomous fix channel working. Closes a GH issue.

**Idea 3 (Step 9E 76d → 45d):**
- WEAKENED: Useful but doesn't close any open issue. The AUTOPILOT_GH_TOKEN is already 41d expired — changing the threshold doesn't help the current problem, only prevents the next one.
- SURVIVES as Bonus B (small SKILL.md edit that takes 5 min alongside the winner).

**Winner of Round 2: Idea 1**

---

## Final Decision

**Winner: Idea 1 — Fix appointment_briefs.py (block_demo_role at router level + structural test)**

- Bonus A: Governance reconciliation (total_runs 105 → 106, last_run update)
- Bonus B: Step 9E threshold 76d → 45d in nightly-commit-review SKILL.md

**Excluded from this run:**
- ai_usage_guard / plan gate: reserve_ai_tokens() requires full tenant dict from DB — adds a DB round-trip and significant complexity. Exceeds XS scope. Filed as follow-up note in mandate.
- pr-backlog-triage SKILL.md: Parking lot until #399 resolved.
- Dependabot escalation: Covered in human-action section of notification.
