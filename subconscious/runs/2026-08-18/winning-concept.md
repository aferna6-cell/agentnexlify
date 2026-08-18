# Winning Concept — 2026-08-18

## Recommendation
Add Step 9I to `.claude/skills/nightly-commit-review/SKILL.md`: a nightly automated sweep that greps `backend/routers/` for mutating endpoints (POST/PUT/DELETE/PATCH) missing `Depends(block_demo_role)`, then auto-files a GitHub issue with `security` + `ai-ready` labels when violations are found that have no existing open issue.

## Why This, Why Now
- **Mandate-triggered:** `governance.json` `run_107_mandate` item 1 requires verifying Step 9I in SKILL.md. It is NOT there. This run is the first carry-forward.
- **Escalation clock running:** Autonomous-executable at run 108 if not approved by human. One run left.
- **Same-class bug filed twice in 6 days:** GH #643 (appointment_briefs.py, 2026-08-11) + GH #661 (scoring_config.py, 2026-08-16). Both caught by humans reading nightly logs. No automated detection exists.
- **Logic proven in the wild:** nightly-2026-08-18 ran the exact Step 9I sweep informally. Found 100+ pre-existing violations, correctly applied skip rules (admin/, webhook routes, public widget routes), correctly applied dedup logic (no bulk issue filing), correctly identified that the two known violations (#643, #661) already have open issues.

## Implementation Sketch
Edit `.claude/skills/nightly-commit-review/SKILL.md` — add after existing Step 9H (or as the final numbered step):

```markdown
## Step 9I — Demo-Role Security Sweep

Check `backend/routers/` for mutating endpoints missing `block_demo_role`:

```bash
for f in backend/routers/*.py; do
  if grep -qE "@router\.(post|put|patch|delete)" "$f"; then
    if ! grep -q "block_demo_role" "$f"; then
      echo "MISSING: $f"
    fi
  fi
done
```

For each file that outputs MISSING:
1. Check whether an open GH issue already exists (search issues with label `security` and the filename in title/body)
2. If open issue exists: skip (dedup)
3. If no open issue: file one via mcp__github__issue_write:
   - title: `[security] {filename}: mutating endpoints missing block_demo_role`
   - body: `Nightly sweep found POST/PUT/DELETE/PATCH endpoints in {filename} not protected by Depends(block_demo_role). Demo tenants can currently write/delete data. Reference: route-security-guard-audit SKILL.md for fix pattern.`
   - labels: `["security", "ai-ready"]`

**Skip conditions (do NOT flag these files):**
- Files with ONLY GET routes (no `@router.post`, `.put`, `.patch`, `.delete`)
- Files under `backend/routers/admin/` prefix
- `stripe_webhooks.py`, `twilio_webhooks.py`, `resend_webhooks.py` — external webhooks
- `widget_chat.py`, `widget_lead.py`, `widget_config.py` — public widget routes
- `auth.py`, `auth_google.py`, `auth_password_reset.py` — auth routes predate the guard pattern
```

## What This Replaces
Run 106 proposed this same winner. This is carry-forward 1. Run 106 winner (Step 9I) is PENDING_HUMAN_APPROVAL. This run confirms the recommendation and advances the escalation clock.

## Parking Lot (for run 108)
**`dependabot-merge-runner` skill:** 4 Dependabot PRs (#629, #630, #631, #649) aging 7-14 days, CI green, safe to merge. Morning digest flags them every day. Skill-discovery-2026-08-17 formally proposed this skill. No blockers. Promote to run 108 if Step 9I is approved/implemented.

## Confidence
HIGH — mandate-triggered, logic proven in nightly-2026-08-18, channel proven (Steps 9C/9E/9F/9G/9H all implemented via SKILL.md edit same channel), implementation is pure SKILL.md text edit (~30 lines), zero product code changes, zero regression risk.

## Autonomous-Executable Status
PENDING_HUMAN_APPROVAL. If not approved or implemented by run 108 (next run), escalates to autonomous-executable per governance escalation protocol (same pattern as runs 97-99 → Step 9F, runs 100-101 → Step 9G, runs 102-104 → route-security-guard-audit SKILL.md).
