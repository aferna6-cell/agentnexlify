# Run 71 Winning Concept — Fix KB Autopopulate Discover Step

**Date:** 2026-06-29  
**Run:** 71  
**Category:** code_health  
**Confidence:** HIGH  
**AUTONOMOUS-EXECUTABLE:** YES  
**Moratorium-safe:** YES  
**Effort:** S (2-line change)

---

## Problem

`scripts/daily/kb-autopopulate.sh` has been broken for 53+ days. The knowledge base receives zero auto-population despite a scheduled twice-daily script. Two bugs compound to block the fallback path:

**Bug 1 — Wrong allowed tools (line 80):**
```bash
"$CLAUDE_BIN" -p "$DISCOVER_PROMPT" \
  --allowedTools Bash,Read,Write,Edit,Glob,Grep \  # ← WebFetch missing
```
The headless Claude session running the discover step cannot call WebFetch — it's not in the allowed list. When agent-browser is unavailable, there is no working fallback.

**Bug 2 — False CLAUDE.md rule in prompt (lines 52-53):**
```
TOOLS: Use agent-browser via Bash (per CLAUDE.md rule: NEVER use WebFetch/WebSearch).
```
This rule does not exist in CLAUDE.md. The parenthetical is false and actively blocks the fallback. Even if WebFetch were in allowed tools, the prompt tells Claude not to use it.

**Result:** agent-browser isn't installed → curl fallback attempted → curl fails in cloud environment (proxy not configured for direct curl) → discover step logs "kb-discover step failed (non-fatal)" → zero new articles.

---

## Fix

File: `scripts/daily/kb-autopopulate.sh`

### Change 1: Add WebFetch to discover step allowed tools (line 80)

```bash
# BEFORE:
"$CLAUDE_BIN" -p "$DISCOVER_PROMPT" \
  --allowedTools Bash,Read,Write,Edit,Glob,Grep \
  --permission-mode bypassPermissions \

# AFTER:
"$CLAUDE_BIN" -p "$DISCOVER_PROMPT" \
  --allowedTools Bash,Read,Write,Edit,Glob,Grep,WebFetch \
  --permission-mode bypassPermissions \
```

### Change 2: Update DISCOVER_PROMPT fallback instruction (lines 52-53)

```bash
# BEFORE (lines 52-53 of the heredoc):
TOOLS: Use agent-browser via Bash (per CLAUDE.md rule: NEVER use WebFetch/WebSearch). Command: `agent-browser fetch <url>` and `agent-browser search <query>`. If agent-browser unavailable, use `curl -sL` to fetch URLs directly.

# AFTER:
TOOLS: Use agent-browser via Bash if available (`agent-browser fetch <url>` and `agent-browser search <query>`). If agent-browser unavailable, use WebFetch tool as the primary fallback. curl -sL is a last resort only.
```

---

## Why This Is AUTONOMOUS-EXECUTABLE

Nightly-commit-review scope includes:
- Bash script line edits (precedent: Check 11 via 061582c, Check 12 via nightly 2026-06-09, Check 13 via nightly 2026-06-17)
- Heredoc / prompt string updates (same file, same scope as bash additions)

Risk: LOW. The change is:
- Additive (adds a tool permission, updates a fallback instruction)
- Reversible (revert 2 lines)
- No schema changes
- No widget changes
- No new dependencies
- No frontend changes

---

## Verification Steps

After the change is committed and the script runs:
1. `knowledge-base/log.md` — should have a new entry from next 6am/6pm run
2. `knowledge-base/raw/<category>/` — should have new files
3. `docs/daily-logs/kb-autopop-YYYY-MM-DD-HH.log` — should show `urls_fetched=N  new_raw_files=N` instead of "kb-discover step failed"

Manual trigger to verify immediately (don't wait for cron):
```bash
bash scripts/daily/kb-autopopulate.sh
```

If cron isn't running in the cloud environment, the script can be invoked manually or integrated into the nightly-commit-review execution flow as a Step 10 addition.

---

## Note on Cron in Cloud Environment

The script assumes cron fires at 6am + 6pm local time. In the remote cloud container, cron jobs may not be configured. If the script never fires autonomously:
- Add a manual trigger to the morning-auto.sh script (already runs daily)
- OR add `bash scripts/daily/kb-autopopulate.sh` as a Step 10 in nightly-commit-review SKILL.md

The WebFetch fix is necessary regardless — it makes the discover step work when the script IS triggered, whether by cron, manual call, or nightly integration.

---

## Files Changed

| File | Line | Change |
|------|------|--------|
| `scripts/daily/kb-autopopulate.sh` | 80 | Add `,WebFetch` to `--allowedTools` |
| `scripts/daily/kb-autopopulate.sh` | 52-53 | Update TOOLS instruction in DISCOVER_PROMPT |

---

## Run 72 Forecast

After KB autopopulate fix: evaluate Record Audit Dashboard (nightly's run 72 candidate). If SMS Compliance Dashboard (run 70 winner) is implemented by run 72, record audit becomes the natural next dashboard item.

Standing actions remain:
- AI-to-Human Handoff v1 (run 4/38, human-required, 75+ days)
- Email sequences split (run 41, human-required)
- Zapier #107 plan_status enforcement (issue-to-pr-loop path, not subconscious winner)
- Widget drift cp command (human-only, docs/reminders/widget-drift-URGENT.md)
