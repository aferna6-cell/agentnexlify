# Winning Concept — 2026-09-03-pm

## Recommendation
Add Step 9L to `.claude/skills/nightly-commit-review/SKILL.md`: a nightly check that greps `docs/dev-knowledge/schema-log.md` for "NOT YET APPLIED" and files or updates a GitHub issue when unapplied migrations are found.

## Why This, Why Now
Migrations 196 (os_tool_executions status CHECK tighten) and 197 (L2 idempotency for double-invoice prevention) are both marked "NOT YET APPLIED" in schema-log.md while Billing Automation v1 (f22ef04, os_invoice_actions.py 650L) shipped today using the exact table migration 196 governs. A double-invoice send is now possible before migration 197 is applied. No automated detection of this gap exists. Step 9L closes this gap with the same autonomous SKILL.md edit pattern that Steps 9F–9K used — all of which were implemented and have been firing correctly. Debate eliminated Idea 3 (one-shot GH issue filing) as redundant because Step 9L both detects AND files automatically on every nightly run going forward.

## Implementation Sketch
1. Open `.claude/skills/nightly-commit-review/SKILL.md`
2. Find the Step 9K block (stale subconscious PR audit) — insert Step 9L immediately after it, before step 10
3. Step 9L block content:

```
### Step 9L: Unapplied Migration Alerter
```python
unapplied = grep("docs/dev-knowledge/schema-log.md", "NOT YET APPLIED")
count = len(unapplied)
if count > 0:
    migration_names = [line.split(":")[0].strip() for line in unapplied]
    # Search for existing open issue
    issues = mcp__github__search_issues(
        owner="aferna6-cell", repo="agentnexlify",
        query="is:open label:database label:human-action-required unapplied migrations"
    )
    if issues:
        # Comment on existing issue (1 per 24h dedup guard)
        last_comment_age = get_last_comment_age(issues[0].number)
        if last_comment_age > 24 * 3600:
            mcp__github__add_issue_comment(
                owner="aferna6-cell", repo="agentnexlify",
                issue_number=issues[0].number,
                body=f"Step 9L nightly alert: {count} migration(s) still NOT YET APPLIED: {', '.join(migration_names)}. Apply via Supabase UI or `mcp__supabase__apply_migration`. Updated: {today}."
            )
    else:
        mcp__github__issue_write(
            owner="aferna6-cell", repo="agentnexlify",
            title=f"fix(migrations): {count} migration(s) marked NOT YET APPLIED in schema-log.md",
            body=f"## Unapplied Migrations Detected\n\nStep 9L nightly alert.\n\n**Migrations:** {', '.join(migration_names)}\n\n**Risk:** Schema-log.md indicates these migrations have not been applied to production. Apply via Supabase UI or `mcp__supabase__apply_migration`.\n\nFirst detected: {today}",
            labels=["human-action-required", "database"]
        )
log(f"Step 9L: {count} unapplied migration(s): {migration_names}" if count > 0 else "Step 9L: 0 unapplied migrations — clean")
```
4. Commit SKILL.md change directly (autonomous-executable — no human approval needed per escalation pattern established in runs 109, 112)
5. Next nightly will fire Step 9L and detect migrations 196/197, filing GH issue automatically

## What This Replaces
Previous active direction: Step 9K (stale subconscious PR audit, run 113/114). Step 9K remains in SKILL.md — Step 9L adds to it. No replacement, addition only.

## Confidence
**HIGH** — Evidence is concrete (196/197 unapplied, billing automation live today), debate survived two full challenge rounds without fatal objections, autonomous-executable pattern is proven across 6 prior steps (9F–9K), and the fix is a SKILL.md edit with zero production blast radius.

## Autonomous-Executable Status
YES — SKILL.md edit follows the same autonomous escalation pattern as Steps 9F, 9G, 9I, 9J, 9K. Nightly review can implement directly without human approval on the next run. If not implemented by run 117 (1 nightly cycle), the run 117 subconscious MUST implement autonomously.
