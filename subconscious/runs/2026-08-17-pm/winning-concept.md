# Winning Concept — 2026-08-17-pm

## Recommendation
Add Step 9I to `.claude/skills/nightly-commit-review/SKILL.md`: a nightly automated sweep that greps `backend/routers/` for mutating endpoints (POST/PUT/DELETE/PATCH) missing `Depends(block_demo_role)`, then auto-files a GitHub issue with `security` + `ai-ready` labels when new violations are found.

## Why This, Why Now
Two identical-class bugs filed in 6 days: GH #643 (appointment_briefs.py, 2026-08-11) and GH #661 (scoring_config.py, 2026-08-16). Both were caught by humans reading nightly logs — not by any automated check. run_106_mandate item 6 explicitly requires proposing Step 9I once route-security-guard-audit SKILL.md is verified in origin (it is — verified PASS this run). The fix closes the entire class: any new router added without `block_demo_role` gets caught within 24 hours instead of whenever someone notices.

## Implementation Sketch
Edit `.claude/skills/nightly-commit-review/SKILL.md` — add after existing Step 9H (or as the final numbered step):

```
## Step 9I — Demo-Role Security Sweep

Check `backend/routers/` for mutating endpoints missing `block_demo_role`:

```bash
grep -rn "def \(create\|update\|delete\|patch\|put\|post\)_\|@router\.\(post\|put\|delete\|patch\)" \
  backend/routers/ \
  --include="*.py" \
  -l
```

For each file found, check whether `block_demo_role` appears in the file's `Depends(...)` imports. If any mutating route in the file lacks it, check whether a GH issue is already open (search issues with label `security` and the filename). If no open issue exists, file one:

```bash
mcp__github__issue_write repo=aferna6-cell/agentnexlify \
  title="[security] {filename}: mutating endpoints missing block_demo_role" \
  body="Nightly sweep found POST/PUT/DELETE/PATCH endpoints in {file} not protected by Depends(block_demo_role). Demo tenants can currently write/delete data. See route-security-guard-audit SKILL.md for fix pattern." \
  labels='["security","ai-ready"]'
```

Skip: GET-only routers, routers under `backend/routers/admin/` (admin-scoped), routers already checked this week (cache by filename in run log).
```

## What This Replaces
This run has no prior active direction to replace. Run 105 winner (git push) was implemented immediately. This is a fresh compound win.

## Confidence
HIGH — mandate-triggered, channel proven (Steps 9C/9E/9F/9G/9H all implemented via SKILL.md edit same channel), implementation is ~30 lines of grep + conditional issue-filing logic, no new dependencies. Only risk is false positives from GET-only routers — mitigated by verb-specific grep pattern.

## Autonomous-Executable Status
This is proposed as **PENDING_HUMAN_APPROVAL** for this run. However, if no human action occurs in 2 consecutive runs (107, 108), this escalates to autonomous-executable via established precedent (runs 97-99 → Step 9F; runs 100-101 → Step 9G; run 102-104 → route-security-guard-audit SKILL.md → implemented run 105).

## Bonus Action
Post targeted comment on GH #403 with exact ANTHROPIC_API_KEY setup steps:
- GitHub repo → Settings → Secrets and variables → Actions → New repository secret
- Name: `ANTHROPIC_API_KEY`
- Value: get from Railway environment variables → agentnexlify backend service → Variables tab
This unblocks 25-day KB staleness in a single minute of user action.
