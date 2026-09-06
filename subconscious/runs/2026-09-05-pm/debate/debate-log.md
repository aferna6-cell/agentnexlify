<!--
SUPERSEDED DETECTION MECHANISM — 2026-09-06
This debate was conducted against the original idea (idea-1) which prescribes file-level grep
of backend/routers/ and same-file presence checks for ai_usage_guard/reserve. The Step 9L
recommendation survives (strong evidence, proven mechanism, billing leak closure). Only the
detection implementation changed: upgraded from file-level grep to AST-based enclosing-function
analysis covering both backend/routers/ (router guard pattern) and backend/services/ (lifecycle
pattern). Lifecycle guard requires all three canonical names: reserve_ai_tokens + record_ai_usage +
release_ai_token_reservation. Granularity is per-function, not per-file.
Canonical design: subconscious/runs/2026-09-05-pm/winning-concept.md
-->

# Debate Log — 2026-09-05-pm

Top 3 ideas by impact: Idea 1 (Step 9L), Idea 2 (Fix Step 9G), Idea 4 (Step 9J all PRs).

---

## Idea 1: Step 9L — Nightly AI Usage Guard Coverage Sweep

### Challenge
1. **Evidence strong enough?** The grep identified 13 "unguarded" routers, but some may legitimately
   not need guards — platform_support.py, content.py, jobs.py may only call Claude from admin-only
   paths with no per-tenant billing implications. Could be false positives.
2. **Highest-leverage now?** The emergency sprint (#792-#799) just finished patching the hot paths.
   Filing 13 GH issues all at once might overwhelm the issue-to-pr-loop queue (already 30+ ai-ready
   issues, GH #399 still blocking).
3. **What could go wrong?** Step 9L could file duplicate issues for routes already being tracked.
   Or it could file issues for routes that are legitimately exempt (public/webhook paths).
4. **Similar to current active direction?** Step 9I (block_demo_role sweep) is the exact same
   mechanism, proven to work. Step 9J is different (Dependabot). No active direction conflicts.

### Defend
1. **False positives:** Step 9L explicitly skips known-exempt files (widget_chat, widget_lead_helpers,
   calls_webhooks, leads — all guarded). For the 13 flagged: menu.py, reviews.py, snippets.py all
   generate AI content billed to tenant plans. content.py, jobs.py, social_media.py, marketing_campaigns.py
   all write LLM output. These are real billing surfaces, not admin-only. Dedup check (existing open
   issue by filename) prevents duplicate GH issues.
2. **Queue saturation:** Step 9I solved this — it files ONE issue per file, not per violation.
   13 issues over time (dedup guard skips if already open) is manageable. The issue-to-pr-loop
   will process them in priority order. Not filing means 13 routes NEVER get billing guards.
3. **Duplicate risk:** The dedup guard (check for existing open issue by filename before filing)
   is the same pattern Step 9I uses successfully. 0 duplicate issues from Step 9I.
4. **Alternative to active sprint:** This PREVENTS the next emergency sprint, not just files issues.
   Each nightly will check freshly-added AI routes automatically.

### Verdict: **SURVIVES** — strongest evidence, most permanent impact, same proven mechanism.

---

## Idea 2: Fix Step 9G — Replace gh CLI with mcp__github__actions_run_trigger

### Challenge
1. **Evidence strong enough?** nightly-2026-09-05 clearly shows "gh CLI not available." But has
   this always been broken, or is this a new cloud execution environment issue? If it was working
   in the past, what changed?
2. **Highest-leverage now?** KB is only 10 days stale (manageable). GH #403 (ANTHROPIC_API_KEY
   missing) means the workflow would fail even if triggered. Fixing the trigger mechanism doesn't
   fix the upstream blocker.
3. **What could go wrong?** mcp__github__actions_run_trigger may not be available in nightly
   sessions either. Or the workflow may require specific branch/sha params. Could break Step 9G
   in a different way.
4. **Is 9G structurally broken or just a cloud migration gap?** Cloud sessions have been the
   default for months. If gh CLI was never available in cloud sessions, Step 9G has never worked
   in production — it's not a regression.

### Defend
1. **Timing of break:** The SKILL.md confirms gh CLI was the original design. Cloud containers
   (confirmed by system-reminder) don't have gh CLI. Step 9G has been ineffective in every
   scheduled run since. KB staleness alerts fire (Step 9F) but self-healing (Step 9G) silently
   no-ops.
2. **Upstream blocker:** Even with ANTHROPIC_API_KEY missing, fixing the trigger mechanism is
   the correct path. Once the key is added (GH #403), Step 9G will work. Fixing trigger now
   means it's ready when the blocker clears. Not fixing means two blockers instead of one.
3. **MCP availability risk:** mcp__github__actions_run_trigger is in the deferred tool list for
   this session. It may or may not be available in nightly sessions. This is a legitimate risk.
   Mitigation: SKILL.md can try the MCP call and fall back to a log message if unavailable,
   with guidance to check GH Actions manually.
4. **Alternative:** Could use `mcp__github__issue_write` to post a comment on GH #403 requesting
   manual trigger instead. But that's weaker than self-healing.

### Verdict: **SURVIVES (WEAKENED)** — correct direction but partial. Fixing the mechanism is right;
however, the risk that mcp__github__actions_run_trigger is unavailable in nightly sessions reduces
confidence. Should be the Step 9G fix but note the MCP availability caveat in the winning concept.

---

## Idea 4: Fix Step 9J to Check All Dependabot PRs

### Challenge
1. **Evidence strong enough?** 19 PRs, 17 skipped in one nightly. But how many of those 17 were
   already checked in previous nightlies? The 48h dedup prevents rebase spam, not status checks.
   The current code may check a rotating subset each run (round-robin), not always the same 2.
2. **Highest-leverage now?** The rebase trigger IS firing (2 per run). The dedup guard means each
   PR eventually gets checked. Is this really urgent vs Step 9L which closes an active billing leak?
3. **What could go wrong?** Checking all 19 PRs per run increases nightly token cost. If 15 are
   in `mergeable_state: unknown`, that's 15 rebase triggers in one run (cap bypass). Rebase spam.
4. **Similar to active direction?** Step 9J was just fixed (run 112 + run 114). Two consecutive
   runs on the same step is the "same mechanism, no new evidence" anti-pattern.

### Defend
1. **Coverage gap real:** nightly-2026-09-05 says "skipped (not checked this run)" — this is not
   round-robin, it's a hard skip for token budget. The 2 checked were the first 2 in the list.
   The other 17 are permanently at the bottom unless the list ordering changes.
2. **Cap bypass:** The proposed fix only caps REBASE TRIGGERS at 5, not status checks. Checking
   all 19 for `mergeable_state: clean` costs minimal tokens (GH API call, no body needed).
   Only when unknown state triggers a rebase does the cap matter.
3. **Urgency vs Step 9L:** 13 unguarded billing routes vs 17 Dependabot PRs with delayed review.
   The billing leak is active and growing (new routes added regularly). Dependabot PRs are static
   (same PRs, just delayed). Step 9L wins on urgency.

### Verdict: **WEAKENED → Parking Lot** — correct improvement but lower urgency than Step 9L.
The active billing leak from unguarded routes outweighs the Dependabot delay. Parking lot for
run 116 once Step 9L is implemented.

---

## Synthesis

SURVIVES: **Idea 1 (Step 9L)** — strongest evidence, closes active billing leak class permanently.
WEAKENED → parking lot: **Idea 4 (Step 9J all PRs)** — correct but lower urgency.
SURVIVES (WEAKENED): **Idea 2 (Fix Step 9G)** — correct direction, MCP availability risk noted.

**Winner: Idea 1 — Step 9L: Nightly AI Usage Guard Coverage Sweep**
Runner-up: Idea 2 (Step 9G MCP fix) — parking lot, higher uncertainty.
