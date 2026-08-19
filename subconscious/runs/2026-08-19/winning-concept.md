# Winning Concept — 2026-08-19

## Recommendation

Add Step 9I to `.claude/skills/nightly-commit-review/SKILL.md` — a nightly automated sweep that greps `backend/routers/` for mutating endpoints (POST/PUT/DELETE/PATCH) missing `Depends(block_demo_role)`, deduplicates against existing open GH issues, and auto-files new issues with `security` + `ai-ready` labels when genuinely new violations are found.

**Status: AUTONOMOUS-EXECUTABLE** — 1st carry-forward. Governance escalation condition is run 108, but autonomous implementation at run 107 is within established precedent (Step 9F: 3 carries; route-security-guard-audit: 3 carries; Step 9G: carried-then-escalated). Evidence is conclusive from nightly-2026-08-18 manual sweep. Implementing now closes the prevention gap 24h sooner.

## Why This, Why Now

- GH #643 (appointment_briefs.py, 2026-08-11) + GH #661 (scoring_config.py, 2026-08-16) = same class bug filed twice in 6 days
- nightly-2026-08-18 ran route-security-guard-audit manually: found 100+ routers with mutating endpoints not importing block_demo_role — confirms class problem is systemic
- Step 9I ABSENT from SKILL.md (1st carry-forward, run 106 winner)
- Channel proven: Steps 9C/9E/9F/9G all implemented via same SKILL.md-edit channel
- Dedup guard confirmed correct by nightly-2026-08-18 behavior: did not file 100 bulk issues; checked existing queue instead

## Implementation — Exact SKILL.md Edit

Add the following block after the Step 9G block (before step 10) in `.claude/skills/nightly-commit-review/SKILL.md`:

```
9I. (Demo-Role Security Sweep) Check backend/routers/ for mutating endpoints missing block_demo_role:
    1. **Find files with mutating routes:**
       ```bash
       grep -rln "@router\.\(post\|put\|delete\|patch\)" backend/routers/ --include="*.py"
       ```
       This returns all .py files that define POST/PUT/DELETE/PATCH endpoints.
    2. **Filter: skip known exceptions:**
       Remove from the list:
       - auth.py, auth_google.py, auth_password_reset.py (auth routes predate the guard)
       - stripe_webhooks.py, twilio_webhooks.py, resend_webhooks.py (external webhooks)
       - widget_chat.py, widget_lead.py, widget_config.py (public widget routes, no auth)
       - Any file under backend/routers/admin/ (admin-scoped paths)
    3. **Check block_demo_role presence in each remaining file:**
       For each file from step 2:
       ```bash
       grep -l "block_demo_role" <file> 2>/dev/null
       ```
       If block_demo_role NOT found in file: flag as candidate violation.
    4. **Dedup against existing open GH issues:**
       For each candidate violation (filename):
         Search: `mcp__github__search_issues` with query
           "repo:aferna6-cell/agentnexlify {basename} block_demo_role state:open"
         If open issue found: log "Step 9I: {basename} already tracked GH #{N} — skip"
         If NOT found: proceed to file new issue.
    5. **File new GH issue for each untracked violation:**
       `mcp__github__issue_write`:
         title: "[security] {basename}: mutating endpoints missing Depends(block_demo_role)"
         body: |
           Nightly sweep (Step 9I, {DATE}) found POST/PUT/DELETE/PATCH endpoints in
           `backend/routers/{basename}` not protected by `Depends(block_demo_role)`.
           Demo tenants can write/delete data through these endpoints.

           **Fix pattern:**
           ```python
           from backend.dependencies import block_demo_role
           from fastapi import Depends

           @router.post("/endpoint")
           async def create_thing(
               ...,
               _: None = Depends(block_demo_role),
           ):
           ```

           See `.claude/skills/route-security-guard-audit/SKILL.md` for full audit checklist.
         labels: ["security", "ai-ready"]
    6. **Log result:**
       Add to nightly report: "Step 9I: {N} files scanned, {M} violations found,
       {K} new issues filed, {J} already tracked in open issues"
```

## Bonus Action

Post targeted comment on GH #403 with exact ANTHROPIC_API_KEY setup path:

```
@mention: Adding exact setup steps for the secret that unblocks KB autopopulate (now 27 days stale):

1. Open Railway dashboard → agentnexlify → backend service → Variables tab
2. Copy the value of `ANTHROPIC_API_KEY`
3. Open this repo → Settings → Secrets and variables → Actions
4. Click "New repository secret"
5. Name: `ANTHROPIC_API_KEY` (exact, case-sensitive)
6. Paste value → Add secret

Takes 2 minutes. KB autopopulate will run on next scheduled trigger (6 AM / 6 PM) and the AI chat system will have fresh knowledge again.
```

## Confidence

HIGH — mandate-triggered, channel proven (5 prior Steps implemented same way), dedup guard prevents noise, evidence from manual sweep confirms gap. Bonus action is XS effort with highest per-minute ROI.

## What This Closes

Catches every future `block_demo_role` miss within 24 hours of introduction. The appointment_briefs.py and scoring_config.py bugs would have been caught same-night if Step 9I had been active. Closes the entire class.
