---
description: Interactive evening routine — review the day and prep for tomorrow.
model: sonnet
---

This command runs the INTERACTIVE evening routine. For the automated version, scripts/daily/evening-auto.sh runs via Task Scheduler (8 PM weekdays).

If the automated evening hasn't run yet, this interactive version will do the full review. If it already ran, read the log and supplement anything it missed.

---

Run the evening review routine for AgentNexLiFy.

## Step 1: Review Today's Work

1. Show all commits from today: git log --since=today --oneline
2. Show all files changed today
3. Identify any fix/bug/patch commits

## Step 2: Update Knowledge Base

For each fix-related commit today:
1. Check if it's documented in docs/dev-knowledge/bug-patterns.md
2. If not, ask me for the root cause and add an entry using the /log-bug format

For each new migration:
1. Check if it's in docs/dev-knowledge/schema-log.md
2. If not, read the SQL and add a summary

## Step 3: End-of-Day Health Check

Run the same checks as morning — compare results:
1. Dangerous imports in routers
2. Bare except count (better or worse than morning?)
3. Widget sync
4. Build status

## Step 4: Update Task Backlog

Update docs/daily-logs/current-tasks.md:
1. Mark completed tasks from today's plan
2. Carry forward unfinished tasks
3. Add any new tasks from the review
4. Set tomorrow's top 3 priorities

## Step 5: Write Evening Log

Append to today's daily log (docs/daily-logs/{today}.md):
- Evening review summary
- Commits and files changed today
- Knowledge base updates made
- Health status comparison (morning vs evening)
- Tomorrow's priorities
