# Improvement Backlog — Run 2026-09-17 (Run 121)

## Active (pending implementation)

### CRITICAL — Step 9E Threshold Fix [2nd carry-forward]
- **What:** Add `days_remaining <= 10` window to Step 9E. Add expiry date to GH comment.
- **Why:** AUTOPILOT_GH_TOKEN expires 2026-10-02 (15 days). Loop dies if not rotated.
- **File:** `.claude/skills/nightly-commit-review/SKILL.md`
- **Effort:** XS
- **Deadline:** Before 2026-10-02. Run 122 = autonomous-executable.
- **Status:** RECOMMENDED (2nd carry)

### HIGH — Step 9G MCP Fix
- **What:** Replace `gh workflow run` with `mcp__github__actions_run_trigger` in Step 9G.
- **Why:** KB autopopulate broken in headless sessions. KB 22d stale (threshold: 7d).
- **File:** `.claude/skills/nightly-commit-review/SKILL.md`
- **Effort:** XS
- **Status:** Runner-up run 121. Recommend bundling with Step 9E.

### MEDIUM — AI Metering Pre-commit Guard
- **What:** Add Check 11 to `check_project_invariants.py`: warn when staged diff adds unguarded AI call.
- **Why:** 45 violations, growing ~5/day. Step 9L detects but doesn't prevent.
- **Files:** `scripts/check_project_invariants.py`, `scripts/install-hooks.sh`
- **Effort:** S
- **Status:** Deferred from run 121. Carry-forward count: 0.

### MEDIUM — Step 9D Idle Escalation
- **What:** Comment on last-closed ai-ready issue when autopilot loop idle for 3+ days.
- **Why:** Loop stalled after #870/#875 closed. No signal to owner.
- **File:** `.claude/skills/nightly-commit-review/SKILL.md`
- **Effort:** XS
- **Status:** Deferred from run 121. Carry-forward count: 0.

### LOW — React 18→19 Migration Checklist
- **What:** Create `docs/dev-knowledge/react-19-migration-checklist.md`.
- **Why:** 4 Dependabot PRs blocked (react-dom, react, vitest major). Human reviewer needs checklist.
- **File:** New doc only.
- **Effort:** M (research + write)
- **Status:** Deferred from run 121. Carry-forward count: 0.

---

## Completed (recent)

- **Run 120 (2026-09-11-pm):** Step 9E GH issue mechanism added (search by label, create if none, comment if exists). Threshold NOT updated — this is the carry-forward.
- **Run 119:** Step 9E first proposed.
- **Run 116 (2026-08-31-pm):** Step 9K implemented — stale subconscious PR audit.
- **Run 113 (2026-08-24):** Step 9J implemented — Dependabot auto-merge.
- **Run 111 (2026-08-19):** Step 9I implemented — demo-role security sweep.
- **Run 109 (2026-09-10-pm):** Step 9L implemented — AI metering coverage sweep.

---

## Frozen (do not re-propose)

- **ai_human_handoff:** Frozen per governance.json. Human approved freeze. Do not carry forward.

---

## Escalation Tracker

| Step | First proposed | Carry count | Status |
|------|---------------|-------------|--------|
| Step 9E threshold | Run 119 | 2 (runs 120+121) | RECOMMEND w/ escalation flag |
| Step 9G MCP fix | Run 121 | 0 | Runner-up |
| AI metering pre-commit | Run 121 | 0 | Deferred |
