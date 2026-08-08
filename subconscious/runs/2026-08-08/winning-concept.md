# Winning Concept — Run 102 (2026-08-08)

## Winner: Nightly Detached HEAD Guard

**Category:** operational
**Effort:** XS (~10 lines bash in SKILL.md)
**Delivery channel:** SKILL.md-edit (autonomous, same class as Steps 9A–9G)
**Requires human approval:** No
**Moratorium impact:** None (SKILL.md-edit does not add to human pending queue)

---

## Problem

nightly-2026-08-07 committed 3 files (ops nightly log, billing_usage.py fixes, morning digest) on a **detached HEAD** — commits were orphaned and never pushed to `origin/main`. Production ran with a MEDIUM security bug (missing `block_demo_role` on `POST /api/v1/billing/buy-usage`) for 24h. Caught and re-applied by nightly-2026-08-08.

Root cause: `.claude/skills/nightly-commit-review/SKILL.md` Scheduled Task Prompt step 2 is `git pull origin main --rebase` but has no prior check that HEAD is on a branch. In remote/cloud execution environments (this Routine runs in an isolated container), HEAD may be detached on session startup. `git pull --rebase` on a detached HEAD does not abort — it proceeds and updates a detached pointer.

---

## Fix: Exact SKILL.md patch (embed verbatim for 1-cycle delivery)

In `.claude/skills/nightly-commit-review/SKILL.md`, find the Scheduled Task Prompt block. Currently:

```
1. cd /home/aidan/agentnexlify
2. git pull origin main --rebase
```

Replace with:

```
1. cd /home/aidan/agentnexlify
1.5. Ensure HEAD is on main branch before any file changes:
   ```bash
   CURRENT_BRANCH=$(git branch --show-current)
   if [ -z "$CURRENT_BRANCH" ]; then
       echo "WARN: detached HEAD detected — switching to main before proceeding"
       git switch main || git checkout main
       if [ $? -ne 0 ]; then
           echo "ERROR: could not switch to main — aborting nightly to prevent orphaned commits"
           exit 1
       fi
   fi
   echo "Branch check PASS: on branch $(git branch --show-current)"
   ```
2. git pull origin main --rebase
```

**Exact file to edit:** `.claude/skills/nightly-commit-review/SKILL.md`

**Exact old string to find:**
```
1. cd /home/aidan/agentnexlify
2. git pull origin main --rebase
```

**Exact new string to insert:**
```
1. cd /home/aidan/agentnexlify
1.5. Ensure HEAD is on main branch before any file changes:
   ```bash
   CURRENT_BRANCH=$(git branch --show-current)
   if [ -z "$CURRENT_BRANCH" ]; then
       echo "WARN: detached HEAD detected — switching to main before proceeding"
       git switch main || git checkout main
       if [ $? -ne 0 ]; then
           echo "ERROR: could not switch to main — aborting nightly to prevent orphaned commits"
           exit 1
       fi
   fi
   echo "Branch check PASS: on branch $(git branch --show-current)"
   ```
2. git pull origin main --rebase
```

---

## Commit message

```
ops(nightly): add detached HEAD guard to SKILL.md step 1.5 [auto-nightly-2026-08-08]
```

---

## Verification after applying

```bash
grep -n "detached HEAD\|CURRENT_BRANCH\|git switch main\|Branch check PASS" .claude/skills/nightly-commit-review/SKILL.md
```

Expected: 4+ matching lines in the 1.5 block.

---

## Why this wins

1. **Direct evidence:** Production bug went unpatched 24h due to exact this failure (2026-08-07 incident, nightly-commit-review log confirms detached HEAD + 3 orphaned commits).
2. **XS effort:** ~10 lines of bash inserted at a known location with embedded verbatim content.
3. **Zero risk:** Guard exits immediately on normal runs (HEAD on main). Only activates when HEAD is detached. Abort-on-fail is correct behavior — better to abort than to orphan commits.
4. **Autonomous delivery:** SKILL.md-edit is the proven autonomous channel (Steps 9A–9G, runs 40/42/43/47/50, all delivered in 1 nightly cycle).
5. **Prevents entire class:** Fixes not just 2026-08-07 but any future remote session that starts on a detached HEAD.

---

## Parking lot carry-forwards

See `improvement-backlog.md` for full list.

- **Step 9F/9G zero-commit path** — verify in mandate: do Steps 9F/9G execute on zero-commit nights?
- **Grandfathered plan gate audit** — verify with grep; file GH issues for gaps
- **response_score.py ai_usage_guard audit** — verify routing before next tenant uses feature
- **Step 9H redesign** — idempotent pile-up alerter (4 subconscious PRs open)
