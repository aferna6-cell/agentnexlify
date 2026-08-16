# Run 106 — Ideation (2026-08-14)

## Context

- Governance: total_runs 102 (stale) → reconciled to 106
- Branch: subconscious/run-103 (runs 103-105 committed here but never updated governance)
- Run 105 winner: appointment_briefs.py security fix (AUTONOMOUS-EXECUTABLE, pending_autonomous)
- Nightly check: fix NOT applied by nightly (nightly operates on main; PR #653 unmerged)
- GH #643: still open, 7 days, no linked PR

## 5 Candidate Ideas

### Idea 1: Apply appointment_briefs.py security fix directly (GH #643)
- **Category**: code_health / security
- **Effort**: XS (~10 min)
- **Evidence**: block_demo_role absent (confirmed grep). GH #643 open 7d, labeled ai-ready+security. Run 105 cleared AUTONOMOUS-EXECUTABLE. Nightly can't apply from unmerged branch. billing.py:33 is canonical pattern. route-security-guard-audit SKILL.md exists (run 104) with exact steps.
- **Risk**: LOW — additive dependencies=[Depends(block_demo_role)] at router level, matching billing.py exactly.

### Idea 2: Create pr-backlog-triage SKILL.md (cycle 2 carry-forward)
- **Category**: workflow_efficiency
- **Effort**: S (~30 min)
- **Evidence**: Run 103 recommended, run 105 parking-lotted. 4 dependabot PRs aging 9-10d, 1 subconscious PR (#626) open 10d. PR pile is real but autopilot stalled (#399).
- **Risk**: MEDIUM — no existing precedent for this skill; human must merge before useful.

### Idea 3: Update Step 9E threshold from 76d to 45d in nightly SKILL.md
- **Category**: operational
- **Effort**: XS (~5 min)
- **Evidence**: AUTOPILOT_GH_TOKEN last rotated 2026-07-04 (41d), Step 9E threshold is 76d warning → no alert fires. 45d would have triggered 2d ago. Prior incident: same credential pair expired same day with no advance warning.
- **Risk**: LOW — SKILL.md edit, no code change.

### Idea 4: File GH issue for dependabot PRs escalation
- **Category**: operational
- **Effort**: XS (~5 min)
- **Evidence**: 4 dependabot PRs (#649/#629/#630/#631) aging 9-10d. Safe merges (patch/minor). Human needs explicit ask.
- **Risk**: LOW — comment only.

### Idea 5: Governance reconciliation — update governance.json total_runs to 106
- **Category**: operational/meta
- **Effort**: XS (~5 min)
- **Evidence**: governance.json shows total_runs=105 (branch) but 4 branch runs never updated state files. Correct count = 102 base + 4 branch = 106.
- **Risk**: NEGLIGIBLE — meta-state only.
