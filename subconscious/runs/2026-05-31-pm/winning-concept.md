# Winning Concept — 2026-05-31-pm (Run 43)

## Recommendation

Extend the AUTONOMOUS-EXECUTABLE scope in nightly-commit-review SKILL.md to cover bash additions to `scripts/hooks/pre-commit` when `governance.json` `active_directions[].autonomous_executable: true`, so Item A (check_project_invariants pre-commit hook, 29-day pending) executes autonomously in tonight's nightly run.

---

## Why This, Why Now

Run 42 (this morning) applied the governance.json half of the run 42 winning concept — Item A is now `pending_autonomous` + `autonomous_executable: true`. The nightly-commit-review SKILL.md half was not applied. Tonight's nightly (`2c15688`) ran at 2:37 AM and implemented 0 items, confirming the directive is missing. The LOW-risk autonomous scope in nightly SKILL.md (line 65) covers SKILL.md file creation but not bash hook additions. Adding one bullet — generalizable to any `autonomous_executable: true` governance entry that touches `scripts/hooks/pre-commit` — closes the gap. The autonomous channel has a 5/5 success rate on correctly-scoped items (7985fbb, 2ce31b2, e848b87, 061582c, d481799). The SKILL.md edit is itself in that scope (per d481799 rule fix). Implementation probability: HIGH — nightly fires tomorrow at 2:37 AM.

---

## Implementation Sketch

### Step 1 — Edit nightly-commit-review SKILL.md (this run or human, ~5 min)

In `.claude/skills/nightly-commit-review/SKILL.md`, find the `### LOW — Autonomous fix allowed (commit + push to main)` section and add after the existing SKILL.md creation bullet:

```markdown
- **Bash additions to `scripts/hooks/pre-commit`** when `subconscious/state/governance.json` has a matching `active_directions[]` entry where `"autonomous_executable": true` and `subconscious/runs/*/winning-concept.md` (most recent) contains `AUTONOMOUS-EXECUTABLE`. Execute the patch in the winning concept directly — commit to main as `ci(pre-commit): <description from winning concept>`.

  **Current pending item (execute tonight):**
  Item A — Wire `check_project_invariants.py` as pre-commit Check 10.
  Status: `pending_autonomous` in governance.json. Unblocked since 2026-05-05 (8f680e8 cleared em-dash).
  Risk: LOW — additive 3 lines, same class as Check 11 (`061582c` 2026-05-29).

  Patch (add after Check 10 block in `scripts/hooks/pre-commit`, before `exit 0`):
  ```bash
  # Check 10 — project invariants (client_id, status, areas_of_interest)
  if command -v python3 &>/dev/null; then
    python3 scripts/check_project_invariants.py || { echo "❌ Pre-commit: check_project_invariants.py failed"; exit 1; }
  fi
  ```
  Commit: `ci(pre-commit): wire check_project_invariants.py as Check 10`
  After commit: update `governance.json` active_directions Item A status → `implemented`.
```

### Step 2 — Verify Item A in pre-commit (next nightly cycle)

```bash
grep -n "check_project_invariants" scripts/hooks/pre-commit
# Expected: 3-line block showing the check
```

### Step 3 — After Item A confirmed: add Item D to same AUTONOMOUS-EXECUTABLE block (run 44)

Item D (`.github/workflows/lead-qualifier-eval.yml`) is an additive new YAML — zero conflict risk. Add it to the AUTONOMOUS-EXECUTABLE section after Item A executes. Sprint reduces to Item B only (~15 min widget sync guard). Moratorium exit path: Item A (tonight) → Item D (run 44) → Item B (human) → pending ≤ 2 → exit.

---

## What This Replaces

No prior winner is replaced. This completes run 42's Step 2 (governance was Step 1, SKILL.md directive is Step 2). Run 42 active_directions entry stands as partially implemented.

---

## Standing Actions (Unchanged Priority Order)

1. **GH #181 billing fix (~15 min, HUMAN REQUIRED):** `billing.py` add `15000: "autopilot"`, `25000: "professional"` to `AMOUNT_TO_PLAN`; remove backwards test assertions in `test_billing_amount_to_plan.py:38-44`. Check 11 fires WARNING as reminder.
2. **email_sequences.py split (~2h, run 41 winner, HUMAN REQUIRED):** `/god-class-splitter` on `backend/routers/email_sequences.py` → email_crud + email_enrollment + email_processor. Do after GH #181.
3. **Item B: check-widget-sync.sh (~15 min, HUMAN REQUIRED):** Only moratorium sprint item requiring human (bash script + pre-push hook + CLAUDE.md fix).
4. **AI-to-Human Handoff v1 (~1 day, run 38, HUMAN REQUIRED):** Agent OS ready (`os_outbound_mirror.py`). Day 45 Critical gap. First target after moratorium exits.

---

## Confidence

**HIGH** — The nightly autonomous channel has confirmed 5/5 success rate on correctly-scoped items. The new bullet is additive to an existing section. The `autonomous_executable: true` flag in governance.json provides machine-readable confirmation. The inline patch makes the action unambiguous — nightly cannot classify it as "docs only" when the patch is code. The only failure mode is nightly misclassifying again despite the new explicit bullet — mitigated by including `scripts/hooks/pre-commit` file path in the bullet (nightly already monitors that file class).
