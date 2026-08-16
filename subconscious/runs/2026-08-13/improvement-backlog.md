# Run 104 — Improvement Backlog (2026-08-13)

Ordered by urgency. Items 1-2 are carry-forward escalations; items 3-5 are new recommendations.

---

## EXECUTED THIS RUN

### route-security-guard-audit SKILL.md
- **Status**: EXECUTED (escalation cycle 3)
- **File**: `.claude/skills/route-security-guard-audit/SKILL.md`
- **Evidence**: 3 commits + GH #643 + 2 prior recommendation cycles
- **Action**: Created directly per governance.json run_104_mandate

---

## ESCALATION PENDING (cycle 2 — run 105 should create directly)

### pr-backlog-triage SKILL.md
- **Status**: PENDING_APPROVAL → escalation pending for run 105
- **File**: `.claude/skills/pr-backlog-triage/SKILL.md`
- **Evidence**: 10 open PRs, 4 Dependabot 10+ days old, morning digest flagging daily, run 103 recommendation unactioned
- **Run 105 action**: If still missing → CREATE DIRECTLY (cycle 3 threshold)
- **Estimated effort**: S (~20 min)

---

## NEW RECOMMENDATIONS

### nightly-commit-review Detached HEAD Guard
- **Status**: NEW RECOMMENDATION
- **Target**: `.claude/skills/nightly-commit-review/SKILL.md` — add pre-commit bash guard
- **Evidence**: cbbaae5 (2026-08-07) orphaned commits, c204af2 (2026-08-08) re-applied, skill-discovery-2026-08-10 explicit proposal
- **Estimated effort**: XS (~10 min)
- **Snippet**:
  ```bash
  BRANCH=$(git symbolic-ref HEAD 2>/dev/null)
  if [ -z "$BRANCH" ]; then git checkout main && git pull origin main; fi
  # After commits: git symbolic-ref HEAD must output refs/heads/main
  ```

### Step 9E credential rotation warning threshold reduction
- **Status**: NEW RECOMMENDATION
- **Target**: `nightly-commit-review` SKILL.md Step 9E section — reduce 76-day threshold to 45 days
- **Evidence**: AUTOPILOT_GH_TOKEN failed loop for 33+ days before human noticed; 76-day threshold never alerted
- **Estimated effort**: XS (~5 min)

### feature-build SKILL.md 5-file pattern
- **Status**: NEW RECOMMENDATION
- **Target**: `.claude/skills/feature-build/SKILL.md` — add "Standard 5-file set" section
- **Evidence**: skill-discovery-2026-08-10 §"Existing Skill Updates #2", e0e9be6 + 4853c31 both follow identical pattern
- **Estimated effort**: XS (~10 min)

---

## HUMAN ACTION REQUIRED (unchanged)

| Item | Issue | Status | Days open |
|---|---|---|---|
| Rotate AUTOPILOT_GH_TOKEN | #399 | OPEN | 33+ days of loop failure |
| Set GitHub Secrets (ANTHROPIC_API_KEY etc.) | #403 | OPEN | KB partial only |
| Fix appointment_briefs.py block_demo_role | #643 | OPEN | 7 days |
| Merge PR #653 | subconscious/run-103 | DRAFT | 1 day |
| Review Dependabot PRs | #649, #629, #630, #631 | OPEN | 10+ days |
