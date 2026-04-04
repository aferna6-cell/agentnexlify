#!/usr/bin/env bash
# Auto-commit changes when Claude finishes a response
# Creates atomic commits per task instead of one big blob

# Drain stdin
cat < /dev/stdin > /dev/null 2>&1

REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_DIR"

# Only auto-commit if there are staged or unstaged changes
if git diff --quiet && git diff --cached --quiet; then
    exit 0
fi

# Don't auto-commit .env files or secrets
git add -A -- ':!.env*' ':!*.pem' ':!*.key' ':!secrets/'

if ! git diff --cached --quiet; then
    # Get the branch name for context
    BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

    git commit -m "chore(ai): auto-commit Claude edits [$BRANCH $TIMESTAMP]" 2>/dev/null
fi

exit 0
