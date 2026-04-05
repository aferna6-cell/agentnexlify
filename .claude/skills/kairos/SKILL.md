---
name: kairos
description: "Persistent background agent. Start/stop the KAIROS daemon for memory consolidation, project monitoring, and dream reports. Use when user says 'kairos start', 'kairos stop', 'kairos status', or 'what did kairos find'."
allowed-tools: Read, Bash, Glob, Grep
---

# KAIROS -- Persistent Background Agent

A daemon that runs between Claude Code sessions to consolidate memory, monitor project health, and surface insights. It does NOT modify any source or memory files -- it only generates reports.

## Quick Commands

### Start the daemon
```bash
bash /home/aidan/agentnexlify/scripts/kairos/daemon.sh start
```
Default interval: 30 minutes. Override with:
```bash
KAIROS_INTERVAL=900 bash /home/aidan/agentnexlify/scripts/kairos/daemon.sh start
```

### Stop the daemon
```bash
bash /home/aidan/agentnexlify/scripts/kairos/daemon.sh stop
```

### Check status
```bash
bash /home/aidan/agentnexlify/scripts/kairos/daemon.sh status
```

### Run one cycle manually (foreground)
```bash
bash /home/aidan/agentnexlify/scripts/kairos/daemon.sh run
```

## Output Files

All output goes to `docs/kairos/`:

| File | Purpose |
|------|---------|
| `dream-YYYY-MM-DD.md` | Memory consolidation report (contradictions, stale refs, freshness) |
| `health-YYYY-MM-DD.md` | Project health report (build, uncommitted changes, code smells, migrations) |
| `dream-log.md` | Append-only summary table of all dream runs |
| `daemon.log` | Daemon process log (start/stop/cycle output) |

## Reading Reports

When the user asks "what did kairos find" or similar:

1. Read the latest dream report:
   ```
   ls -t docs/kairos/dream-*.md | head -1
   ```
   Then read that file.

2. Read the latest health report:
   ```
   ls -t docs/kairos/health-*.md | head -1
   ```
   Then read that file.

3. For a historical view, read `docs/kairos/dream-log.md`.

## What Each Script Does

### autodream.py (Memory Consolidation)
- Reads all memory files from the Claude projects memory directory
- Reads dev-knowledge files (bug-patterns, schema-log, architecture-decisions)
- Reads 24h of git commit history
- Checks for contradictions between files (wrong column names, old plan names, conflicting values)
- Checks for stale references (memory files pointing to files that no longer exist)
- Checks memory freshness (files with only old dates)
- Detects duplicate information spread across files
- Writes findings to `docs/kairos/dream-YYYY-MM-DD.md`
- NEVER modifies memory files -- only reports what should change

### monitor.py (Project Health)
- Checks frontend for syntax issues (without running a full build)
- Flags uncommitted changes older than 24h
- Scans recent commits for TODO/FIXME/HACK and dangerous patterns
- Cross-references migration files against schema-log.md
- Checks for dangerous `from __future__ import annotations` in backend routers
- Verifies .env files are not tracked by git
- Writes findings to `docs/kairos/health-YYYY-MM-DD.md`

## Architecture

```
daemon.sh (bash, runs via nohup)
  |
  +-- autodream.py (python3, stdlib only)
  |     reads: memory files, dev-knowledge, git log
  |     writes: docs/kairos/dream-*.md, dream-log.md
  |
  +-- monitor.py (python3, stdlib only)
        reads: frontend/, backend/, migrations/, schema-log.md, git status/diff
        writes: docs/kairos/health-*.md
```

PID file: `/tmp/kairos.pid`
Log file: `docs/kairos/daemon.log`

## Safety

- Read-only analysis. No destructive operations.
- No pip dependencies. Standard library only.
- No network calls (except git, which is local).
- No file modifications outside `docs/kairos/`.
- If any check fails, it logs the error and continues to the next check.

## Troubleshooting

**Daemon won't start:** Check if `/tmp/kairos.pid` exists with a stale PID. Remove it manually.

**Reports are empty:** Run `bash scripts/kairos/daemon.sh run` in foreground to see errors.

**Dream report shows 0 memory files:** The memory directory path may have changed. Check `MEMORY_DIR` in `autodream.py`.
