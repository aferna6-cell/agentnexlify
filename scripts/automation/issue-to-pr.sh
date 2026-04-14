#!/usr/bin/env bash
# issue-to-pr.sh — poll open issues, classify, dispatch subagent, open PR
# run by cron every 15 min. See .claude/skills/issue-to-pr-loop/SKILL.md
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"
TS="$(date -Iseconds)"
echo "[$TS] start" >&2

# --- config ---
ASSIGNEE="${ASSIGNEE:-@me}"
MAX_CONCURRENT="${MAX_CONCURRENT:-1}"
BUDGET_USD="${ANTHROPIC_BUDGET_USD:-5}"
BRANCH_PREFIX="auto/issue"

# --- guardrails ---
command -v gh >/dev/null || { echo "gh not installed"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh not authed"; exit 1; }
command -v claude >/dev/null || { echo "claude CLI not installed"; exit 1; }

# --- pick issue ---
issue_json="$(gh issue list \
  --assignee "$ASSIGNEE" \
  --state open \
  --json number,title,body,labels,url \
  --limit 20)"

pick="$(echo "$issue_json" | jq -r '
  [.[] | select(
    ([.labels[].name] | inside(["wip-auto","auto-pr","auto-failed","needs-info"]) | not)
  )][0]
')"

if [ "$pick" = "null" ] || [ -z "$pick" ]; then
  echo "[$TS] no eligible issues"
  exit 0
fi

N="$(echo "$pick" | jq -r .number)"
TITLE="$(echo "$pick" | jq -r .title)"
BODY="$(echo "$pick" | jq -r .body)"
URL="$(echo "$pick" | jq -r .url)"

echo "[$TS] picked #$N: $TITLE" >&2

# --- mark wip ---
gh issue edit "$N" --add-label "wip-auto" >/dev/null

# --- classify ---
CLASSIFY_PROMPT=$(cat <<EOF
You are a triage agent. Decide if this GitHub issue is ready for an AI subagent to implement end-to-end.

Issue #$N: $TITLE

$BODY

Return STRICT JSON, no prose:
{"ready": true|false, "reason": "...", "clarifying_questions": ["..."]}

Ready = goal concrete, files identifiable, success criteria inferable, no architecture decisions needed, no new secrets required.
EOF
)

classification="$(echo "$CLASSIFY_PROMPT" | claude -p --model claude-haiku-4-5-20251001 --output-format text 2>/dev/null || echo '{"ready":false,"reason":"classifier failed","clarifying_questions":["rerun manually"]}')"

ready="$(echo "$classification" | jq -r .ready 2>/dev/null || echo false)"

if [ "$ready" != "true" ]; then
  reason="$(echo "$classification" | jq -r .reason 2>/dev/null || echo 'not ready')"
  qs="$(echo "$classification" | jq -r '.clarifying_questions | map("- " + .) | join("\n")' 2>/dev/null || echo '- needs review')"
  gh issue comment "$N" --body "🤖 **Auto-triage**: not ready for AI implementation.

**Reason**: $reason

**Clarifying questions**:
$qs"
  gh issue edit "$N" --remove-label "wip-auto" --add-label "needs-info"
  echo "[$TS] #$N → needs-info"
  exit 0
fi

# --- execute in worktree ---
SLUG="$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '-' | cut -c1-40 | sed 's/-*$//')"
BRANCH="$BRANCH_PREFIX-$N-$SLUG"
WT_DIR="$REPO_ROOT/.worktrees/issue-$N"

git worktree remove -f "$WT_DIR" 2>/dev/null || true
git worktree add -b "$BRANCH" "$WT_DIR" origin/main

EXEC_PROMPT=$(cat <<EOF
Implement GitHub issue #$N end-to-end. Follow CLAUDE.md and karpathy-guidelines strictly.

Issue: $TITLE
$BODY

Rules:
- surgical changes, don't touch unrelated files
- tests for new behavior
- run relevant build/test before committing
- commit: "feat: $TITLE\n\nCloses #$N"
- do NOT push or open PR yourself — the harness will

Forbidden: _archive/, landing-page-v2/, public/, from __future__ imports, localStorage in React, tenant_id/lead_stage in leads table.
EOF
)

cd "$WT_DIR"
echo "$EXEC_PROMPT" | claude -p --model claude-sonnet-4-6 --dangerously-skip-permissions 2>&1 | tee "$LOG_DIR/issue-$N.log"

# --- check for commits ---
if ! git log origin/main..HEAD --oneline | grep -q .; then
  echo "[$TS] #$N no commits produced"
  gh issue edit "$N" --remove-label "wip-auto" --add-label "auto-failed"
  git worktree remove -f "$WT_DIR"
  exit 1
fi

# --- push + PR ---
git push -u origin "$BRANCH"
PR_URL="$(gh pr create \
  --title "feat: $TITLE" \
  --body "Closes #$N

🤖 Auto-implemented by issue-to-pr-loop.

## Test plan
$(git log origin/main..HEAD --oneline)

## Issue
$URL" \
  --base main \
  --head "$BRANCH")"

gh issue edit "$N" --remove-label "wip-auto" --add-label "auto-pr"
gh issue comment "$N" --body "🤖 PR opened: $PR_URL"

cd "$REPO_ROOT"
git worktree remove -f "$WT_DIR" 2>/dev/null || true

echo "[$TS] #$N → $PR_URL"
