# Idea 5: Governance.json verified_implemented schema (prevent stale flags)

**Evidence:**
- Run 119 mandate found Step 9L flag stale: `implemented: false` in governance.json even though Step 9L confirmed at SKILL.md lines 457/471. Run 118 spent time re-verifying.
- Run 119 parking lot: "governance.json verified_implemented schema".
- Pattern: every few runs, mandate check must re-verify already-implemented steps because flags drift.
- Current schema has `implemented: true/false` and `implemented_date` but no `verified_date` field.

**Action:**
1. Add `verified_date` field to active_directions entries in governance.json.
2. Update Step 9L entry: set `verified_date: "2026-09-10-pm"`, confirm `implemented: true`.
3. Document convention: `verified_date` = date subconscious confirmed implementation via grep/read (not just governance flag).

**Impact:**
Reduces mandate check time. Prevents re-verification loops. Low effort (doc + governance edit).

**Weakness:**
Not directly revenue-connected. Low urgency vs credential expiry.

**Category:** workflow_efficiency

**Effort:** XS (governance.json + convention doc)

**Confidence:** MEDIUM — addresses real governance drift but low leverage vs Idea 1.
