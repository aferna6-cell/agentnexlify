#!/usr/bin/env bash
# pr-feedback.sh — pick an open auto-pr with unresolved review comments, implement them
# run by cron every 10 min. See .claude/skills/issue-to-pr-loop/SKILL.md
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"
TS="$(date -Iseconds)"

command -v gh >/dev/null || exit 1
gh auth status >/dev/null 2>&1 || exit 1
command -v claude >/dev/null || exit 1

# find oldest open PR with auto-pr label on its linked issue
pr_json="$(gh pr list --state open --json number,headRefName,title,url --limit 20)"
pick="$(echo "$pr_json" | jq -r '[.[] | select(.headRefName | startswith("auto/issue-"))][0]')"

if [ "$pick" = "null" ] || [ -z "$pick" ]; then
  exit 0
fi

PR_NUM="$(echo "$pick" | jq -r .number)"
BRANCH="$(echo "$pick" | jq -r .headRefName)"
PR_URL="$(echo "$pick" | jq -r .url)"

# fetch unresolved review comments
comments="$(gh api "repos/:owner/:repo/pulls/$PR_NUM/comments" --jq '[.[] | select(.in_reply_to_id == null) | {id, path, body, line}]')"
count="$(echo "$comments" | jq 'length')"

if [ "$count" -eq 0 ]; then
  exit 0
fi

echo "[$TS] PR #$PR_NUM has $count unresolved comments" >&2

WT_DIR="$REPO_ROOT/.worktrees/pr-$PR_NUM"
git worktree remove -f "$WT_DIR" 2>/dev/null || true
git fetch origin "$BRANCH"
git worktree add "$WT_DIR" "origin/$BRANCH"
cd "$WT_DIR"
git checkout "$BRANCH"

FEEDBACK_PROMPT=$(cat <<EOF
Implement unresolved review comments on PR #$PR_NUM ($PR_URL).

Comments (JSON):
$comments

Rules:
- one commit per comment
- if a comment asks for changes beyond PR scope, SKIP it and note in the commit message
- run relevant tests/build before each commit
- follow CLAUDE.md + karpathy-guidelines
- do NOT push — the harness will
EOF
)

echo "$FEEDBACK_PROMPT" | claude -p --model claude-sonnet-4-6 --dangerously-skip-permissions 2>&1 | tee "$LOG_DIR/pr-$PR_NUM.log"

if git log "origin/$BRANCH..HEAD" --oneline | grep -q .; then
  git push origin "$BRANCH"
  gh pr comment "$PR_NUM" --body "🤖 Applied $count review comment(s). Please re-review."
fi

cd "$REPO_ROOT"
git worktree remove -f "$WT_DIR" 2>/dev/null || true
echo "[$TS] PR #$PR_NUM done"
