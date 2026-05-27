# Winning Concept — 2026-05-27 (Run 36)

## Recommendation

Create `.claude/skills/post-split-test-repair/SKILL.md` — an 8-step checklist that repoints stale `@patch` decorators and import paths in test files after any god-class split or module rename.

---

## Why This, Why Now

**The pattern has fired twice in one week with 100% recurrence.** `5f2cd2b` ("test: repoint stale patch targets and imports after refactor") repaired 21 stale patch targets across 4 test files after the local_seo split. `4afb3cf` ("Fix test_local_seo_parsers import") fixed a second stale import the same day. Both were predictable follow-up commits — the split moved code, the test `@patch` strings still pointed to the old module path.

**The god-class backlog is large and growing.** 29 backend files + 25 frontend files still exceed 600L per `plans/god-class-refactor_plan.md`. Every split will generate a post-split test-repair pass. Without the skill, that pass is: run pytest, decode the failure, grep old paths, manually update, re-run — ~15–20 min of unencoded rediscovery each time. With the skill, it's a 1-step invocation that runs the checklist automatically.

**email_sequences.py split (run 35 winner) is next.** At 1255L with imports from multiple test files, it will almost certainly generate a repair commit. Creating the skill NOW encodes the checklist before the split happens, not after. The god-class-splitter skill was created for exactly this reason — encode the pattern before the next occurrence.

**The nightly review is the working implementation channel.** Three consecutive autonomous implementations by nightly review (moratorium-sprint SKILL.md, escalation-protocol SKILL.md, god-class-splitter SKILL.md). This recommendation follows the identical pattern: pure new `.md` file, LOW-risk, additive, no production code changes. Implementation probability: HIGH. In moratorium conditions (pending = 10, exit threshold = 2), recommendations that don't require human approval reduce backlog faster than ones that do.

---

## Implementation Sketch

### Step 1: Create the skill file

**Path:** `.claude/skills/post-split-test-repair/SKILL.md`

**Content (authoritative draft):**

```markdown
---
name: post-split-test-repair
description: Repoint stale @patch decorators and import paths in test files after a god-class split or module rename. Prevents the predictable 2-commit waste (split + repair).
version: 1.0.0
origin: subconscious-run-36
user-invocable: true
triggers:
- post-split-test-repair
- repoint patch targets
- stale patch after split
- tests broke after refactor
- ModuleNotFoundError after split
effort: low
---

# Post-Split Test Repair

After any god-class split or module rename, tests that use `@patch("old.module.path")` or
`from old.module import X` will fail with `ModuleNotFoundError` or `AttributeError` until
their references are updated. This skill runs the repair in one pass.

## Trigger conditions

- `pytest` output shows `ModuleNotFoundError: No module named 'backend.routers.old_router'`
- `pytest` output shows `AttributeError: <MagicMock> does not have the attribute 'fn'`
- User says "tests broke after split", "stale patch targets", "repoint imports after refactor"
- Just completed a god-class split (run immediately as step 11.5 of god-class-splitter)

## The 8 Steps

1. **Capture first failure:**
   ```bash
   python3 -m pytest tests/ -x --tb=short -q 2>&1 | head -50
   ```
   Note the old module path in the error (e.g. `backend.routers.local_seo`).

2. **Identify old path:** Extract the old fully-qualified path from the error.
   Common patterns: `backend.routers.<old>`, `backend.services.<old>`.

3. **Grep all test files for old path:**
   ```bash
   grep -rn "backend.routers.<old>\|backend.services.<old>" tests/
   ```

4. **Determine new canonical paths:** Check what was extracted where.
   ```bash
   grep -rn "def <fn_name>" backend/  # find where the function now lives
   ```

5. **Update `@patch` decorators:** For each stale `@patch("old.module.fn")` → `@patch("new.module.fn")`.

6. **Update `from ... import` statements:** For each `from old.module import X` → `from new.module import X`.

7. **Re-run pytest — repeat until green:**
   ```bash
   python3 -m pytest tests/ -x --tb=short -q
   ```
   Cycle steps 1–6 until no stale module errors remain.

8. **Commit:**
   ```bash
   git commit -m "test: repoint stale patch targets and imports after <split-name> refactor"
   ```

## Relationship to god-class-splitter

This skill is step 11.5 of `.claude/skills/god-class-splitter/SKILL.md`. Run it immediately
after step 11 (smoke tests written) if pytest shows module errors. Also run standalone if
test drift compounds days after the split.

## Anti-patterns

- Never fix `@patch` strings by guessing the new path — always grep to confirm the new location.
- Never change test behavior to paper over the error — only update the module path.
- Never run `pytest -k <test_name>` to isolate failing tests during repair — run the full suite
  to catch all stale references in one pass.

## Evidence

- `5f2cd2b`: repaired 21 stale patch targets after local_seo split (2026-05-22)
- `4afb3cf`: fixed stale import in test_local_seo_parsers after same split (2026-05-22)
- PR #180: 5-file split — same repair class expected for any tests importing old service paths
- Skill proposed by skill-discovery report 2026-05-25 (ROI 1.9, parking lot)
```

### Step 2: Update god-class-splitter SKILL.md

Add step 11.5 reference in `.claude/skills/god-class-splitter/SKILL.md`:

After Step 11 ("Write smoke tests"), add:

```
11.5 Run `pytest tests/ -x --tb=short -q`. If any `ModuleNotFoundError` or `AttributeError`
     on MagicMock appears, invoke `post-split-test-repair` before committing.
```

### Step 3: Commit

```bash
git add .claude/skills/post-split-test-repair/SKILL.md
git add .claude/skills/god-class-splitter/SKILL.md
git commit -m "workflow(skills): add post-split-test-repair — repoint stale @patch after module splits"
```

---

## Standing Actions (Not Changed by This Recommendation)

These remain the highest-priority human-required items:

1. **GH #181 billing fix (~15 min):** `billing.py` add `15000: "autopilot"` + `25000: "professional"` to AMOUNT_TO_PLAN; remove inverted test assertions. Do this before email_sequences split.
2. **email_sequences.py split (~2h, run 35 winner):** Invoke `/god-class-splitter email_sequences.py`. Pre-condition: GH #181 fixed first. Pattern: review PR #182 before starting.
3. **Moratorium sprint Items A/B/D (~40 min):** check_project_invariants pre-commit, widget sync guard, CI eval workflow.

---

## What This Replaces

Previous active direction was email_sequences.py split (run 35 winner). That recommendation stands as the **highest-priority human-required action** — it is not superseded, only deprioritized in the winner slot for run 36. Run 35's entry in `active_directions` is not changed.

Run 36 adds post-split-test-repair as a NEW active direction (autonomously executable). The two coexist — one for the nightly review channel, one for the human channel.

---

## Confidence

**HIGH** — Evidence is clear (100% recurrence rate, 2 repair commits in one week, explicit skill-discovery proposal). Execution channel is proven (3 consecutive autonomous implementations by nightly review). No implementation blockers. The only uncertainty is whether nightly review fires before the email_sequences split happens — but even if the split runs first, the skill will still be valuable for all 54+ remaining god-class targets.
