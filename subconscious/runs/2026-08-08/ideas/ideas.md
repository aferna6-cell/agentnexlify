# Ideas — Run 102 (2026-08-08)

Evidence window: last 3 days git log + nightly logs 2026-08-07/08 + bug patterns + parking lot

---

## Idea 1 — Nightly detached HEAD guard

**Category:** operational  
**Effort:** XS (~5 lines bash in SKILL.md)  
**Evidence:** nightly-2026-08-07 ran on detached HEAD — 3 commits (97e1044, cbbaae5, 7dff08b) orphaned and never pushed to origin/main. Production had unpatched MEDIUM bug (billing_usage.py missing block_demo_role) for 24h. Caught and re-applied by nightly-2026-08-08. Root cause: SKILL.md Scheduled Task Prompt step 2 is `git pull origin main --rebase` — no prior guard ensures HEAD is on main. In remote/cloud sessions HEAD can be detached on startup.

**Fix:** Insert between step 1 and step 2 in SKILL.md Scheduled Task Prompt:
```bash
CURRENT_BRANCH=$(git branch --show-current)
if [ -z "$CURRENT_BRANCH" ]; then
    echo "WARN: detached HEAD detected — switching to main"
    git switch main || git checkout main
    if [ $? -ne 0 ]; then
        echo "ERROR: could not switch to main — aborting to prevent orphaned commits"
        exit 1
    fi
fi
```
**Autonomous:** Yes — SKILL.md-edit channel, same class as Steps 9A–9G (all implemented in 1 cycle).

---

## Idea 2 — Step 9F/9G zero-commit path coverage

**Category:** operational  
**Effort:** XS (~2-line condition change in SKILL.md)  
**Evidence:** nightly-2026-08-08 had "0 commits on main in last 24h" and Step 4 of Scheduled Task Prompt says "If zero commits: write empty report, exit." This means Step 9F/9G (KB staleness check) is skipped entirely on zero-commit nights. KB is currently 16 days stale. If nightly encounters zero-commit nights repeatedly, Step 9G never fires to trigger the autopopulate workflow.

**Fix:** Move Step 9F/9G execution BEFORE the zero-commit early-exit in the Scheduled Task Prompt:
- Execute steps 9F and 9G (KB staleness) before the "If zero commits: write empty report, exit" check
- KB staleness is independent of commit volume

**Autonomous:** Yes — SKILL.md-edit channel.

---

## Idea 3 — Grandfathered plan gate audit

**Category:** code_health / revenue  
**Effort:** S (grep + read files + file GH issues)  
**Evidence:** 2869124 fixes AI Workforce gate missing grandfathered plan check. Class-of-bug: other gates may check `plan == "agent_os"` without including `growth|autopilot|professional|enterprise`. CLAUDE.md documents grandfathered plans must be honored. Parking lot item from run 101.

**Fix:** 
1. `grep -rn 'plan.*==.*"agent_os"\|plan.*in.*\["agent_os"\]' backend/` 
2. For each hit, verify `growth`, `autopilot`, `professional`, `enterprise` are included in the gate condition
3. File GH issue per gap found with labels `revenue`, `medium-risk`

**Autonomous:** Partially — grep + file issues is in nightly LOW-risk scope. Code fixes are MEDIUM (need human approval).

---

## Idea 4 — response_score.py ai_usage_guard routing audit

**Category:** code_health / cost  
**Effort:** XS (read file, grep, file GH issue if gap found)  
**Evidence:** commit e0e9be6 (2026-08-06) ships response_score.py (151 lines, Claude-calling service). Nightly reviewed at MEDIUM risk but did NOT verify ai_usage_guard routing. widget_guard.py precedent (run 94) shows this class matters. Parking lot item from run 101.

**Fix:** Read `backend/services/response_score.py`. Verify:
1. Does it import from `ai_usage_guard`?
2. Does it call `get_ai_usage_status()` or equivalent before API calls?
3. If missing: file GH issue with labels `cost-protection`, `medium-risk`, `ai-ready`

**Autonomous:** Yes — read + grep + file GH issue is in nightly scope.

---

## Idea 5 — Step 9H redesign: idempotent PR pile-up alerter

**Category:** operational  
**Effort:** S (~20 lines in SKILL.md + governance.json tracking field)  
**Evidence:** 4 open subconscious draft PRs: #626, #613, #611, #606. Prior Step 9H design rejected at run 100 because it fired every nightly (noise without convergence). New design: track `last_pile_alert_count` in governance.json; only alert when open subconscious PR count INCREASES from last check. Idempotent — alerts once per increment, not per run.

**Fix:** Add Step 9H to SKILL.md:
1. List open PRs with `subconscious` in head branch via mcp__github__list_pull_requests
2. Compare count to `governance.last_pile_alert_count`
3. If count > last_count: comment on GH #403 with "subconscious PR pile grew to N" and update governance field
4. Only fires on INCREASE (not just when pile exists)

**Autonomous:** Partially — SKILL.md-edit is autonomous, governance.json update is autonomous, GH comment is autonomous. Net: autonomous-executable via SKILL.md channel.
