# Run 104 — Candidate Ideas (2026-08-13)

## Evidence Summary

- **Velocity**: LOW — only ops/log commits in last 48h, no feature code
- **Escalation active**: `route-security-guard-audit` SKILL.md MISSING after 2 recommendation cycles (runs 102 + 103 carry-forward). governance.json run_104_mandate: CREATE DIRECTLY.
- **PR pile-up**: 10 open PRs — #653 (subconscious DRAFT), #648, #626, #613, #611, #606, #604, #649, #629, #630, #631. 4 Dependabot PRs (#649, #629, #630, #631) aging 10+ days with security patches unmerged.
- **AUTOPILOT_GH_TOKEN**: #399 not rotated. Loop failing 33+ days. Step 9E warning threshold (76 days) never flagged it before failure.
- **pr-backlog-triage SKILL.md**: MISSING. Run 103 winner (cycle 2 now — escalation pending for run 105).
- **nightly-commit-review Detached HEAD Guard**: cbbaae5 orphaned (2026-08-07), c204af2 re-applied (2026-08-08). Same 15-min fix cost paid twice. SKILL.md still missing the guard.
- **KB**: Step 9G triggered kb-autopopulate.yml (2026-08-13). 10 new articles indexed. Embeddings skipped (no ANTHROPIC_API_KEY). Partial recovery.
- **GH #643**: Still open, no PR linked, autopilot stalled.

---

## Idea 1 — route-security-guard-audit SKILL.md [ESCALATION]

**Category**: code_health  
**Effort**: XS (~10 min — content drafted in run 102 winning-concept.md, copy + adjust)  
**Escalation**: Cycle 3 — governance mandate says CREATE DIRECTLY (no human approval needed)

### What
Create `.claude/skills/route-security-guard-audit/SKILL.md` with the 6-step audit checklist drafted in run 102. Escalation trigger: same precedent as Step 9F (run 99, 3rd recommendation cycle → direct implementation).

### Evidence
- `cbbaae5` (2026-08-07): nightly applied fix on detached HEAD — commits orphaned
- `c204af2` (2026-08-08): same fix re-applied correctly
- `228203d` (2026-08-08): structural test added
- GH #643 (open 7 days): appointment_briefs.py still missing `block_demo_role`
- Run 102 + run 103 carry-forward: 2 recommendation cycles with no human approval

### Why it works
SKILL.md creation is documentation-only. No backend code touched. No implementation risk. The content already exists in run 102 artifacts — this is copy-and-finalize work. At cycle 3, the escalation rule in governance.json supersedes the approval gate.

---

## Idea 2 — pr-backlog-triage SKILL.md [ESCALATION PENDING]

**Category**: workflow_efficiency  
**Effort**: S (~20 min)  
**Escalation**: Cycle 2 — recommend again; next run (105) triggers direct creation if still missing

### What
Create `.claude/skills/pr-backlog-triage/SKILL.md` — classifies open PRs into merge-ready/superseded/stale-draft/active, produces triage table, autonomous Dependabot merge gate.

### Evidence
- 10 open PRs as of 2026-08-13 (4 Dependabot aging 10+ days with security patches)
- Morning digest flagged PR pile-up as Top 3 priority on consecutive days
- skill-discovery-2026-08-10: explicit proposal with ~20 min/triage saved estimate
- Run 103 winner (2026-08-12-pm): RECOMMENDED, human not yet approved

### Limitation
Cycle 2 — governance rules allow one more recommendation before escalation. Carrying forward is correct per protocol.

---

## Idea 3 — nightly-commit-review Detached HEAD Guard

**Category**: code_health  
**Effort**: XS (~10 min — 4-line bash snippet added to existing SKILL.md)

### What
Add bash guard to `.claude/skills/nightly-commit-review/SKILL.md` pre-commit section:
```bash
BRANCH=$(git symbolic-ref HEAD 2>/dev/null)
if [ -z "$BRANCH" ]; then
  git checkout main && git pull origin main
fi
```
Run after commit: `git symbolic-ref HEAD` must output `refs/heads/main`.

### Evidence
- `cbbaae5` (2026-08-07): nightly committed to detached HEAD → 3 commits orphaned
- `c204af2` (2026-08-08): same fix re-applied after discovery (30+ min cost)
- skill-discovery-2026-08-10 §"Existing Skill Updates": explicitly proposed this with code snippet

### Why this matters now
Regardless of run 104 winner, run 103's winner was already documented in PR #653 title. This is a different skill update — modifying an EXISTING SKILL.md, not creating a new one. Could run in parallel with the escalation winner.

---

## Idea 4 — Step 9E Credential Rotation Warning Threshold Reduction

**Category**: operational  
**Effort**: XS (~5 min — change one number in SKILL.md)

### What
Reduce Step 9E warning threshold from 76 days to 45 days in `nightly-commit-review` SKILL.md. Current: token aged 40 days at failure start, warning never fired. Root cause: 76-day warning threshold is too loose when autopilot loop runs daily.

### Evidence
- AUTOPILOT_GH_TOKEN: estimated 40 days since rotation (per 2026-08-13 nightly log)
- Loop has been failing 33+ days (since ~2026-07-11)
- GH #399 still open — human has not rotated despite 33+ nightly log entries
- Step 9E runs nightly but "OK (< 76-day warning)" never triggers an alert before damage

### Limitation
Doesn't solve the current failure (token still needs rotation). Prevents the NEXT occurrence. A warning alone is advisory — the issue is human action latency, not detection latency. Considered low-leverage vs escalation action.

---

## Idea 5 — feature-build SKILL.md 5-File Pattern Documentation

**Category**: workflow_efficiency  
**Effort**: XS (~10 min — add one section to existing SKILL.md)

### What
Add "Standard 5-file set" section to `.claude/skills/feature-build/SKILL.md` pre-build checklist (content from skill-discovery-2026-08-10):
```
backend/routers/<feature>.py
backend/services/<feature>.py
backend/tests/test_<feature>.py
frontend/src/pages/<Feature>.jsx
frontend/src/utils/api/<feature>.js
```

### Evidence
- skill-discovery-2026-08-10 §"Existing Skill Updates #2": proposed with evidence from e0e9be6 and 4853c31 following identical pattern
- Current feature-build SKILL.md doesn't name the canonical 5-file set → future features guess

### Limitation
Low urgency — missing documentation causes friction but not bugs. Weaker than security/escalation candidates.
