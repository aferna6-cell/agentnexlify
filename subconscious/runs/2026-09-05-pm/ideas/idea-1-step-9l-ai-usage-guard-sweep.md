<!--
SUPERSEDED — 2026-09-06
This file prescribes router-level grep / same-file presence checks, which is the original
approach from the idea brainstorm. The winning concept adopted AST-based enclosing-function
analysis (function-granularity, not file-granularity) with import alias resolution, proper
lifecycle discrimination (reserve_ai_tokens + record_ai_usage + release_ai_token_reservation
all required), and `client.messages.create` AST chain detection.

Canonical design: `subconscious/runs/2026-09-05-pm/winning-concept.md`
Do NOT use the grep / same-file approach described below for any implementation.
-->

### Idea 1: Add Step 9L — Nightly AI Usage Guard Coverage Sweep

**Evidence:**
Direct grep (2026-09-05) confirms 13 routers call `call_claude_messages` without any `ai_usage_guard`:
menu.py, widget_photo_quote.py, platform_support.py, content.py, jobs.py, snippets.py, reviews.py,
os_files.py, onboarding.py, insights.py, bids.py, marketing_campaigns.py, social_media.py.
PRs #792–#799 (last 3 days) were an emergency billing-guard retrofit for voice/widget/SMS — 7 PRs in
3 days. Each added 600–1726 lines of tests. This reactive cost repeats forever without a preventative gate.
Step 9I (block_demo_role sweep) has prevented 2+ security class-bugs since implementation. Same mechanism
would close the billing-leak class permanently.

**Action:**
Add Step 9L block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9K:
1. `grep -rln "call_claude_messages\|from anthropic import" backend/routers/` — find AI-calling routers.
2. For each file, check if `ai_usage_guard` or `reserve` is imported/present.
3. Exclude known-exempt routes: widget_chat.py (guarded), widget_lead_helpers.py (guarded),
   calls_webhooks.py (guarded), leads.py (guarded), and public/webhook paths.
4. For each unguarded file: check for existing open GH issue by filename; if none, file issue with
   labels `billing + ai-ready`. Skip if already open.
5. Log: "Step 9L: {N} AI-calling routers checked, {M} unguarded, {K} issues filed."

**Impact:**
Closes the billing-leak class permanently. 13 currently unguarded routes get GH issues queued.
issue-to-pr-loop will implement them. No more reactive 7-PR sprints.
Category: code_health / billing
Effort: S (SKILL.md edit only, same autonomous-executable channel as Step 9I)
