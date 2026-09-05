# Winning Concept — Run 115 (2026-09-05-pm)

## Recommendation
Add Step 9L to `.claude/skills/nightly-commit-review/SKILL.md` — a nightly AI usage guard coverage
sweep that identifies routers calling `call_claude_messages` without `ai_usage_guard`, and files
GH issues (labels: `billing + ai-ready`) for each unguarded route.

## Why This, Why Now
13 routers are confirmed unguarded as of 2026-09-05 (direct grep): menu.py, widget_photo_quote.py,
platform_support.py, content.py, jobs.py, snippets.py, reviews.py, os_files.py, onboarding.py,
insights.py, bids.py, marketing_campaigns.py, social_media.py. PRs #792–#799 (last 3 days) were a
7-PR emergency sprint to retrofit billing guards on voice/widget/SMS paths — each adding 600-1726
lines of tests. Without a preventive nightly sweep, every new AI route added to the codebase starts
unguarded and accumulates billing debt until a human notices and kicks off another sprint. Step 9I
(block_demo_role sweep) follows the identical mechanism and has caught security class-bugs since
implementation. Step 9L applies that proven mechanism to the billing domain.

## Implementation Sketch
1. Edit `.claude/skills/nightly-commit-review/SKILL.md` — insert Step 9L block after Step 9K
   summary log line and before "10. Commit report" step.

**Step 9L block to insert:**
```markdown
### Step 9L — AI Usage Guard Coverage Sweep

1. Find AI-calling router files:
   ```bash
   grep -rln "call_claude_messages\|from anthropic import" backend/routers/ --include="*.py"
   ```
2. For each file, check if `ai_usage_guard` or `ai_usage_guard.reserve` is present:
   ```bash
   grep -l "ai_usage_guard\|\.reserve(" backend/routers/<file>.py
   ```
3. Skip known-guarded or known-exempt files:
   - widget_chat.py, widget_lead_helpers.py, calls_webhooks.py, leads.py (confirmed guarded)
   - auth.py, auth_google.py, stripe_webhooks.py, twilio_webhooks.py, resend_webhooks.py (no billing surface)
4. For each remaining unguarded file:
   a. Check for existing open GH issue by searching title containing the filename.
      `mcp__github__search_issues(query="repo:aferna6-cell/agentnexlify is:open {filename} ai_usage_guard")`
   b. If no existing open issue: file GH issue via `mcp__github__issue_write`:
      Title: "fix(billing): {filename} calls Claude without ai_usage_guard — billing leak"
      Labels: ["billing", "ai-ready"]
      Body: "Router {filename} calls `call_claude_messages` without `ai_usage_guard.reserve/record/release`.
      AI spend from this route is untracked and unbilled. Add the guard pattern per PRs #792–#799.
      Autodetected by Step 9L nightly sweep."
   c. If existing open issue found: skip (dedup guard).
5. Log result:
   "Step 9L: {N} AI-calling routers checked, {M} unguarded, {K} issues filed, {D} dedup-skipped."
```

2. The same commit should also add Step 9L to the nightly report summary section.

3. **Autonomous-executable:** This is a SKILL.md edit only — same channel as Steps 9C/9E/9F/9G/9I/9J/9K.
   No backend code changes, no migrations, no new state files.

## What This Replaces
Active direction was Step 9K (implemented run 114, working correctly as of nightly-2026-09-05).
Step 9L extends the nightly sweep pattern to a new domain (billing vs. security). No replacement
of prior active direction — additive.

## Confidence
**HIGH** — Evidence is direct (grep confirmed 13 unguarded routes today). Mechanism proven (Step 9I
identical pattern, zero false positive issues in 5+ weeks). Risk is dedup failure (mitigated by
search_issues check before filing). Token cost is low (bash greps + conditional GH API calls).

## Escalation Condition
Autonomous-executable if not approved by run 116 (1st carry-forward mandate per established governance).
