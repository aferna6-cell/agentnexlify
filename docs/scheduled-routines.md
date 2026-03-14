# Scheduled Routines — AgentNexLiFy

The morning and evening routines run automatically using `claude -p` (headless mode) on a schedule. They analyze the repo, update documentation, and prepare task plans — all without human intervention.

They use the machine's local date for log/report filenames, record a small static health snapshot before the headless agent starts, and fail fast with a clear log entry if the Claude CLI cannot be resolved at runtime.

## What the Morning Routine Does

**Script:** `scripts/daily/morning-auto.sh`
**Schedule:** 8 AM weekdays
**Duration:** ~5-10 minutes

1. **Health Check** — Scans for dangerous imports, bare except blocks, hardcoded secrets, .gitignore completeness, widget sync, TODO/FIXME comments
2. **Activity Analysis** — Reviews last 24h of git activity, identifies undocumented bug fixes and schema changes
3. **Task Generation** — Creates a prioritized task list (P1 critical → P4 improvements), carries forward unfinished tasks
4. **Safe Auto-Fixes** — Updates schema-log.md with undocumented migrations, adds skeleton entries to bug-patterns.md for undocumented fix commits
5. **Daily Log** — Writes `docs/daily-logs/{date}.md` with results, task plan, and agent delegation recommendations
6. **Commit** — Stages and commits all docs/ changes (does NOT push)

## What the Evening Routine Does

**Script:** `scripts/daily/evening-auto.sh`
**Schedule:** 8 PM weekdays
**Duration:** ~5-10 minutes

1. **Commit Review** — Reviews all commits and file changes from today
2. **Knowledge Base Updates** — Adds undocumented bug fixes to bug-patterns.md, documents new migrations in schema-log.md
3. **Health Check** — Runs same checks as morning for comparison
4. **Task Backlog Update** — Marks completed tasks, carries forward unfinished work, sets tomorrow's top 3 priorities in `docs/daily-logs/current-tasks.md`
5. **Evening Log** — Appends evening section to today's daily log
6. **Commit** — Stages and commits docs/ changes (does NOT push)

## Safety Boundaries

### What the automated routines CAN do:
- Read any file in the repo
- Write/edit files ONLY in `docs/` directory
- Run git log, git add, git commit, git pull, git diff, git status
- Run grep, find, cat, ls, wc, head, tail, sort, diff, echo, date, mkdir

### What they CANNOT do:
- Run npm, pip, python, node, curl, wget, or any package manager
- Delete files (rm is blocked)
- Run sudo commands
- Modify application code (backend routes, frontend components, widget)
- Run database migrations
- Touch .env files
- Push to remote (developer pushes manually)

The routines currently run with `claude -p --dangerously-skip-permissions`. Safety comes from the repo instructions and the prompts themselves, which still tell the headless session to keep automated edits inside `docs/`.

## Shared Health Check

Use `bash scripts/daily/health-check.sh` for the shared static checks. It reports:
- dangerous imports in `backend/routers/`
- bare `except:` count
- silent async catch count in frontend/backend JS/TS
- widget file sync
- `.env` coverage in `.gitignore`

## Setup

### Windows (Task Scheduler)

Run once in PowerShell as Administrator:

```powershell
cd C:\path\to\agentnexlify
powershell -ExecutionPolicy Bypass -File scripts\daily\setup-scheduler.ps1
```

To customize times:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\daily\setup-scheduler.ps1 -MorningTime "09:00" -EveningTime "21:00"
```

### WSL / Linux / macOS (Cron)

```bash
bash scripts/daily/setup-cron.sh
```

To customize times (hour minute for morning, then evening):

```bash
bash scripts/daily/setup-cron.sh 9 0 21 0
```

If `claude` was installed or moved after the scheduler was first created, rerun the setup script. The setup scripts now persist the resolved Claude CLI path for cron and inject the Claude CLI directory into the Windows Task Scheduler wrapper PATH.

Optional override for manual runs or custom schedulers:

```bash
export AGENTNEXLIFY_CLAUDE_BIN=/absolute/path/to/claude
```

## Checking It Works

### View scheduled tasks (Windows)

```powershell
Get-ScheduledTask -TaskName 'AgentNexLiFy-*' | Format-Table TaskName, State
```

### Test manually (Windows)

```powershell
Start-ScheduledTask -TaskName 'AgentNexLiFy-Morning'
```

### Test manually (WSL/Linux)

```bash
bash scripts/daily/morning-auto.sh
```

### Check execution logs

```bash
# Raw execution log (gitignored)
cat docs/daily-logs/auto-morning-$(date +%Y-%m-%d).log

# Evening raw execution log (same local date basis)
cat docs/daily-logs/auto-evening-$(date +%Y-%m-%d).log

# Daily report (committed)
cat docs/daily-logs/$(date +%Y-%m-%d).md

# Task backlog
cat docs/daily-logs/current-tasks.md
```

### Check git for auto-commits

```bash
git log --oneline --grep="automated morning\|automated evening"
```

## Temporarily Disabling

### Windows
Open Task Scheduler → find AgentNexLiFy-Morning/Evening → right-click → Disable

### Cron
```bash
crontab -e  # comment out the AgentNexLiFy lines
```

## Removing Completely

### Windows
```powershell
powershell -ExecutionPolicy Bypass -File scripts\daily\remove-scheduler.ps1
```

### Cron
```bash
crontab -l | grep -v AgentNexLiFy | crontab -
```

## How Interactive Commands Complement Automation

The `/morning` and `/evening` slash commands in Claude Code run the same routines interactively:

- If the automated run already happened, the interactive command reads the auto-generated log and picks up where it left off — focusing on tasks that need human judgment
- If the automated run didn't happen (machine was off), the interactive command does the full routine
- The interactive version can execute code changes that the automated version is restricted from doing

## The Self-Improvement Loop

```
Morning reads knowledge base → analyzes repo → generates tasks
    ↓
Developer (or agents) work on tasks during the day
    ↓
Evening reviews commits → updates knowledge base → prepares tomorrow
    ↓
Next morning reads updated knowledge base → is smarter about the repo
```

Each cycle makes the system more aware of patterns, bugs, and priorities. The knowledge base files (bug-patterns.md, schema-log.md, architecture-decisions.md) accumulate institutional memory that persists across sessions.
