# Winning Concept — 2026-07-29 (Run 103)

## Recommendation
Add Step 9G CORRECTED to `.claude/skills/nightly-commit-review/SKILL.md`: after Step 9F fires the staleness alert, check `git log --since="48 hours ago" -- knowledge-base/` to verify CCR Routine recently committed KB updates. If no KB commits AND KB stale >7 days → comment on GH #403 "CCR Routine may be stalled."

Also bundle: correct Step 9F's diagnostic text (still points to defunct GH Actions path).

## Why This, Why Now

KB staleness as of 2026-07-29: **6 days** (last CCR run: 2026-07-23). The 7-day threshold fires **tomorrow (2026-07-30)**. Step 9F (staleness alert) WILL fire in tomorrow's nightly and comment on GH #403 with the wrong diagnostic ("Check ANTHROPIC_API_KEY in GitHub Actions secrets"). GH Actions are broken repo-wide (#500). The CCR Routine is the active path.

Without Step 9G CORRECTED:
- Tomorrow's nightly alerts (Step 9F fires) — correct
- No health check on whether CCR is actually stalled vs. just behind — missing
- Step 9F comment text misleads owner toward a dead-end debugging path (GH Actions secrets) — wrong

With Step 9G CORRECTED:
- After Step 9F fires, Step 9G checks git log for recent KB activity
- If CCR has recent commits: Step 9G logs "CCR healthy" and suppresses redundant alert
- If CCR is genuinely stalled: Step 9G posts a specific "CCR Routine may be stalled" message that points to the right path (cloud Routine, not GH Actions)

**Direct implementation this run** (consistent with run 102's direct god-class-splitter SKILL.md implementation). XS effort, zero production risk, proven channel.

## Full Pseudocode — Step 9G CORRECTED

Insert between Step 9F (ends at "9F: KB STALE — comment added to GH #403") and Step 10 ("Commit report...") in `.claude/skills/nightly-commit-review/SKILL.md`:

```
   5. **Step 9G: CCR Routine health check** (runs only if Step 9F determined days_stale > 7):
      a. Check recent KB commits: `git log --since="48 hours ago" --oneline -- knowledge-base/`
      b. If output is empty (no KB commits in 48h):
         Post comment via mcp__github__add_issue_comment:
           issue_number: 403
           body: "**Step 9G: CCR Routine health check.** KB is {days_stale} days stale AND no KB commits found in the last 48h. The CCR Routine ('KB Auto-Populate (CCR)') may be stalled or not scheduled. Verify the Routine is active at claude.ai/code. Note: this alert fires when BOTH conditions hold — KB stale >7 days AND no recent KB commits. A PR in-flight from CCR may not yet show here."
         If GH comment fails: log "Step 9G: comment failed (token may be expired)" and continue.
         Log: "Step 9G: CCR stall alert posted to GH #403 — KB stale {days_stale}d, no commits in 48h"
      c. If KB commits found:
         Log: "Step 9G: CCR healthy — KB commits found in last 48h (days_stale: {days_stale})"
      Note: This is the CORRECTED design replacing the original Step 9G (gh workflow run kb-autopopulate.yml).
            CCR Routine handles KB autopopulate via cloud Routine — NOT GH Actions.
            GH Actions are broken repo-wide (#500). Original design is OBSOLETE.
```

## Step 9F Diagnostic Text Correction (bundle with same commit)

In Step 9F block (line 303 in current SKILL.md), replace:

**Before:**
```
body: "**KB autopopulate staleness alert (Step 9F):** {days_stale} days since last successful run (last: {last_run_date}). Check: (1) ANTHROPIC_API_KEY in GitHub Actions secrets — may need rotation. (2) SUPABASE_ACCESS_TOKEN — may be expired. Manual trigger: `bash scripts/daily/kb-autopopulate.sh`."
```

**After:**
```
body: "**KB autopopulate staleness alert (Step 9F):** {days_stale} days since last CCR Routine run (last: {last_run_date}). The CCR Routine ('KB Auto-Populate (CCR)') handles KB autopopulate. Check if it is active at claude.ai/code. GH Actions path is NOT the active path (#500). Step 9G will follow with a detailed CCR health check."
```

## What "directly implemented" means

Both Step 9G CORRECTED and the Step 9F text correction are implemented in this subconscious commit (same branch: `subconscious/run-2026-07-28`). The winning-concept.md is the recommendation record; the SKILL.md edit is the execution. This follows the run 102 precedent (god-class-splitter SKILL.md update implemented on this branch, not deferred to nightly).

## Carry-forward: feature-docs-trio SKILL.md

Still missing. This is the **2nd carry-forward** (run 101 = 1st proposal, run 102 = 1st carry-forward, run 103 = 2nd carry-forward). **3rd carry-forward fires direct implementation in run 104.**

Full content for run 104 to implement directly:

```markdown
---
name: feature-docs-trio
description: After any feature PR merges, produce KB wiki article + ADR entry + INDEX update + optional runbook in one [skip ci] commit. Trigger within 48h of feature landing.
---

## Trigger
Feature PR merged with no corresponding docs commit in 48h. User says "docs for <feature>", "kb article for <feature>", "document <feature>".

## Steps

1. **Read PR** — extract feature name, key decisions, tier gates, failure modes.

2. **Write `knowledge-base/wiki/<category>/<feature-name>.md`**:
   - Frontmatter: `title`, `category`, `tags`, `last_updated`
   - Required sections: What it does, How it works (prose flow diagram), Tier gate, Failure modes, Related articles (wikilinks)
   - Run `npm run kb:lint` — must be clean before committing

3. **Add ADR entry to `docs/dev-knowledge/architecture-decisions.md`**:
   - Format: `ADR-YYYY-MM-DD-NNN — <title>` + 2-3 sentence rationale + alternatives rejected

4. **Update `knowledge-base/INDEX.md`** under correct category section.

5. **Write `docs/runbooks/<feature>-failures.md`** (only if feature has on-call-actionable failure modes):
   - Format per failure class: symptom → root cause → fix steps

6. **Commit** as `docs(<feature>): KB article + ADR + runbook [skip ci]`
```

Also update `feature-build/SKILL.md` to add after the main build steps:
```
After the feature PR merges, run `feature-docs-trio` to produce KB article + ADR + runbook in a follow-up `docs(<feature>): [skip ci]` commit.
```

## Backlog

1. **(HIGH, run 104 direct implementation) feature-docs-trio SKILL.md** — 2nd carry-forward → direct at run 104. Full content embedded above.
2. **(MEDIUM) Silent-green tenant heartbeat (Step 9H)** — nightly query of conversations table for paid tenants with 0 conversations/7d. Prerequisite: verify SUPABASE_URL + SUPABASE_SERVICE_KEY available in nightly CCR bash environment. Use `client_id`, NOT `tenant_id`.
3. **(LOW) widget-ai-marker-add SKILL.md** — 2 occurrences, ~1/month. Byte-identical sync is the error-prone step.
4. **(LOW) round-iteration-loop SKILL.md** — 3 occurrences in 7 days per skill-discovery.

## Confidence
**HIGH** — Same SKILL.md bash block channel as Steps 9B–9F. Evidence is time-boxed: KB threshold fires tomorrow, wrong diagnostic text fires with it. XS effort. Zero production risk (SKILL.md edits only affect nightly pseudocode executor).
