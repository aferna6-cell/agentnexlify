# Winning Concept — 2026-05-29 (Run 39)

## Recommendation

Create `.claude/skills/post-split-test-repair/SKILL.md` — an 8-step checklist for repointing stale `@patch` targets and imports after module splits — so that the email_sequences.py god-class split (run 35 winner, 1255L) can be executed as a single clean PR without follow-up repair commits.

---

## Why This, Why Now

Three commits confirm a 100% recurrence rate: every god-class split or API-cleanup migration generates stale `@patch` targets (`5f2cd2b`, `4afb3cf`, `bca2082` — one per split/migration in 6 days). Without the repair guide, the email_sequences.py split will produce a 4th repair commit, turning a clean 1-PR operation into a split PR + CI-red + repair PR sequence. The nightly review `061582c` (2026-05-29) confirmed the autonomous channel is active by implementing Check 11 (run 37 winner). Today's nightly log explicitly lists post-split-test-repair as Standing Action #5, signaling the review is aware and queued to implement it. The three prior SKILL.md autonomous implementations (`7985fbb`, `2ce31b2`, `e848b87`) all used the "AUTONOMOUS-EXECUTABLE" label in the preceding winning-concept — this run uses the same label.

---

## Implementation Sketch

**AUTONOMOUS-EXECUTABLE: nightly review should implement this directly, without human instruction. This is a LOW-risk pure new .md file, consistent with autonomous implementations 7985fbb (moratorium-sprint SKILL.md), 2ce31b2 (moratorium escalation protocol), e848b87 (god-class-splitter SKILL.md).**

### File to create: `.claude/skills/post-split-test-repair/SKILL.md`

Content (8-step checklist):

```markdown
---
name: post-split-test-repair
description: Repair stale @patch targets and imports after any module split or API cleanup migration. Invoke immediately after every god-class split or migration that relocates symbols.
version: 1.0.0
triggers:
- after god-class split
- after module extraction
- after API cleanup migration
- stale @patch error
- ImportError after split
---

# Post-Split Test Repair

Run this checklist after EVERY module split before committing. Takes ~15 min. Prevents CI-red repair commits.

## Step 1: Find all test files that import split symbols
\`\`\`bash
grep -rn "from backend.routers.<old_module> import\|from backend.services.<old_module> import" backend/tests/
\`\`\`

## Step 2: Find all @patch decorators targeting old module paths
\`\`\`bash
grep -rn "@patch.*<old_module>" backend/tests/
\`\`\`

## Step 3: For each stale path, determine the new module
Check the split output: which symbol moved to which new file?
- CRUD functions → email_crud.py (or equivalent)
- Enrollment logic → email_enrollment.py
- Processing logic → email_processor.py

## Step 4: Update @patch paths
Replace old module path with new path. Pattern:
- `@patch("backend.routers.email_sequences.send_email")` → `@patch("backend.services.email_crud.send_email")`
- `@patch("backend.services.widget_helpers.get_lead")` → `@patch("backend.services.widget_lead_helpers.get_lead")`

## Step 5: Update import statements in test files
Replace:
\`\`\`python
from backend.routers.email_sequences import list_sequences
\`\`\`
With:
\`\`\`python
from backend.services.email_crud import list_sequences
\`\`\`

## Step 6: Check for re-exports in __init__.py
If the old module re-exported symbols via `__init__.py`, ensure the new modules are also exported. Add to `backend/services/__init__.py` if needed.

## Step 7: Run the test suite for affected modules only
\`\`\`bash
python -m pytest backend/tests/ -k "email or <split_module_name>" -x --tb=short
\`\`\`
Fix any remaining import errors before committing.

## Step 8: Commit repair in the same PR as the split
Do NOT commit the split without the repair. One PR = split + repair. If repair is discovered post-commit, amend before push (not after).

## Recurrence evidence
- 5f2cd2b: test-repair after local_seo.py split
- 4afb3cf: import-repair after local_seo.py split (second repair commit same day)
- bca2082: test-mock-repair after API cleanup migration (.filter() chain fix)
100% recurrence rate on splits and API migrations in this codebase.

## Cross-refs
- `.claude/skills/god-class-splitter/SKILL.md` — add reference to this skill at step 6 ("Run post-split-test-repair")
- `docs/dev-knowledge/bug-patterns.md` — stale @patch pattern
- `god-class-refactor_plan.md` — 54 files remaining (each will need this checklist)
```

### Also update: `.claude/skills/god-class-splitter/SKILL.md`
Add step reference: after the split execution step, add: "Step 6.5: Immediately run post-split-test-repair SKILL.md to repoint stale @patch targets."

---

## What This Replaces

Previous active direction was AI-to-Human Handoff v1 via Agent OS (run 38 winner, pending_approval). That item remains in active_directions as pending_approval — this run's winner is a workflow enabler, not a replacement of the strategic direction. Sequence: post-split-test-repair SKILL.md (autonomous, ~12h) → email_sequences.py split (human, ~2h) → GH #181 fix (human, ~15 min) → AI-to-Human Handoff v1 (~1 day).

---

## Governance Correction Applied This Run

**Run 37 (billing-constant-guard Check 11) status: pending_approval → implemented.**
Evidence: `061582c` (nightly-commit-review 2026-05-29) added Check 11 to `scripts/hooks/pre-commit`. Check 11 fires correctly: `AMOUNT_TO_PLAN missing entries: 15000 25000 — see GH #181`. runs_implemented: 8 → 9.

---

## Standing Actions (Unchanged)

In priority order:

1. **GH #181 billing fix (~15 min, HUMAN REQUIRED):** `billing.py` add `15000: "autopilot"`, `25000: "professional"` to `AMOUNT_TO_PLAN`; remove backwards test assertions `test_billing_amount_to_plan.py:38-44`. Check 11 now fires WARNING on every commit.
2. **AI-to-Human Handoff v1 (~1 day):** `widget_chat.py` trigger detection + `migrations/131_handoff_requests.sql` + `handoff_service.py` + tests via `os_outbound_mirror`. Agent OS plumbing ready (PR #188). Run 38 winner.
3. **Invoke /moratorium-sprint (~40 min):** Items A (check_project_invariants pre-commit Check 10), B (widget sync guard), D (CI eval workflow). Day 26+.
4. **email_sequences.py split (~2h):** invoke `/god-class-splitter email_sequences.py` AFTER post-split-test-repair SKILL.md exists. Run 35 winner.

---

## Confidence

**HIGH** — three prior SKILL.md autonomous implementations with explicit "AUTONOMOUS-EXECUTABLE" label (100% success rate). Nightly review 2026-05-29 confirmed active. Awareness confirmed in standing actions log. Pattern evidence for the SKILL.md content is strong (100% recurrence on 3 commits). One nightly cycle away from unblocking a 2h human task.
