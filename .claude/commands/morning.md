---
description: Interactive morning routine. Use when user starts the day or says morning, what is on.
model: sonnet
allowed-tools: [Bash]
---

## Prefetched context

Current git status:
!`git status --short`

Recent commits:
!`git log --oneline -10`

Commits in last 24h:
!`git log --since='24 hours ago' --oneline | wc -l`

Active plan files:
!`ls plans/*.md 2>/dev/null | head -5`

---

This command runs the INTERACTIVE morning routine. For the automated version, the system runs scripts/daily/morning-auto.sh via Task Scheduler (8 AM weekdays).

If the automated morning already ran today, read docs/daily-logs/ for today's date first. Then pick up where it left off — it may have identified tasks that need human judgment to execute.

---

Run the morning startup routine for AgentNexLiFy. Go through each step:

## Step 1: Health Check

Check the codebase for critical issues:
1. Scan backend/routers/ for `from __future__ import annotations` — CRITICAL if found
2. Count bare `except: pass` blocks in backend Python files
3. Check .env is in .gitignore
4. Check for hardcoded secrets (sk_live_, sk_test_, sk-ant-) in code files
5. Check widget file sync (widget/ vs frontend/public/widget/)
6. Scan for TODO/FIXME comments and count them

## Step 2: Recent Activity

1. Show git log from the last 24 hours
2. Identify any bug fix commits not documented in docs/dev-knowledge/bug-patterns.md
3. Identify any new migrations not in docs/dev-knowledge/schema-log.md

## Step 3: Task Planning

Generate a prioritized task list based on the health check and recent activity:
- P1: Critical issues (security, build failures, dangerous imports)
- P2: Documentation gaps
- P3: Code quality improvements
- P4: Feature work and enhancements

Carry forward unfinished tasks from docs/daily-logs/current-tasks.md.

## Step 4: Update Files

- Write health check results and task plan to docs/daily-logs/{today}.md
- Update docs/daily-logs/current-tasks.md with the prioritized task list
- Auto-fix any documentation gaps (schema-log, bug-patterns)

## Step 5: Recommend Delegation

For tasks requiring code changes, recommend which agent to delegate to:
- schema-guardian for database work
- backend-dev for API changes
- frontend-dev for UI work
- widget-specialist for widget changes
- qa-tester for validation
- devops for deployment
