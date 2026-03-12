Generate a comprehensive summary of all recent changes to the codebase.

## Step 1: Gather Change Data

Run these commands and collect the output:

1. git log --oneline -30 — recent commits
2. git log --since="7 days ago" --oneline — this week's work
3. git log --since="24 hours ago" --oneline — today's work
4. git log --since="7 days ago" --name-only --pretty=format:"" | sort | uniq -c | sort -rn | head -20 — most modified files
5. git log --since="7 days ago" --pretty=format:"%s" — commit messages for categorization

## Step 2: Categorize Changes

Group all commits into:

**Features Built:**
- [list every feat: commit with description of what it adds]

**Bugs Fixed:**
- [list every fix: commit with what was broken and how it was fixed]

**Tests Added:**
- [total test count if you can determine it — run the test suite]
- [list what's tested]

**Code Quality:**
- [list every refactor: or chore: commit]

**Documentation & Knowledge Base:**
- [list every docs: commit]
- [check docs/dev-knowledge/bug-patterns.md — how many entries?]
- [check docs/dev-knowledge/schema-log.md — how many entries?]

**Infrastructure & DevOps:**
- [CI/CD changes, hook changes, agent/skill changes]

**Content Generated:**
- [any marketing copy, help articles, emails created]

## Step 3: Generate Metrics

Calculate:
- Total commits in period
- Files changed
- Features built
- Bugs fixed
- Tests (run the test suite, report total and pass/fail)
- Bundle size (if frontend — run build and note output size)
- Knowledge base size (count entries in bug-patterns.md, schema-log.md, architecture-decisions.md)

## Step 4: Current Health

Run a quick health check:
- Frontend builds?
- Backend imports?
- Tests pass?
- Any dangerous imports or secrets?

## Step 5: Output

Print a clean summary:

```
═══════════════════════════════════════
  AgentNexLiFy — Change Summary
  [date range]
═══════════════════════════════════════

HEALTH: [ALL CLEAR / ISSUES]

METRICS:
  Commits:        [N]
  Features built:  [N]
  Bugs fixed:      [N]
  Tests:           [N] passing
  Bundle size:     [N]KB
  Knowledge base:  [N] bug patterns, [N] schema entries, [N] arch decisions

FEATURES:
  • [feature 1 — one line description]
  • [feature 2]

BUGS FIXED:
  • [bug 1 — what was broken → what was fixed]
  • [bug 2]

TESTS ADDED:
  • [area 1 — N tests]
  • [area 2 — N tests]

CODE QUALITY:
  • [improvement 1]
  • [improvement 2]

CONTENT:
  • [content piece 1]
  • [content piece 2]

INFRASTRUCTURE:
  • [change 1]
  • [change 2]

MOST ACTIVE FILES:
  [top 5 most modified files this period]

BACKLOG STATUS:
  [read .claude/agent-comms/backlog.md and report what's done vs remaining]
```
