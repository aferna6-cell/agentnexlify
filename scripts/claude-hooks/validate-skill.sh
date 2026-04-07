#!/usr/bin/env bash
# Validate SKILL.md files follow the standard template on write.
# PreToolUse hook — blocks writes to .claude/skills/**/SKILL.md that lack required structure.

set -euo pipefail

INPUT=$(cat /dev/stdin)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')

# Only check SKILL.md files in .claude/skills/
if [[ -z "$FILE" ]] || [[ "$FILE" != *".claude/skills/"*"/SKILL.md"* ]]; then
  exit 0
fi

# For Edit tool, file already exists — check after edit (PostToolUse handles this)
# For Write tool, check the content being written
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // empty')

if [[ -z "$CONTENT" ]]; then
  # Edit tool — can't validate content pre-edit, let it through
  exit 0
fi

ERRORS=""

# Check frontmatter exists
if ! echo "$CONTENT" | head -1 | grep -q '^---$'; then
  ERRORS="${ERRORS}Missing YAML frontmatter (must start with ---)\n"
fi

# Check required frontmatter fields
for field in name description version origin triggers; do
  if ! echo "$CONTENT" | grep -q "^${field}:"; then
    ERRORS="${ERRORS}Missing frontmatter field: ${field}\n"
  fi
done

# Check required sections
for section in "## When to Use" "## When NOT to Use"; do
  if ! echo "$CONTENT" | grep -q "$section"; then
    ERRORS="${ERRORS}Missing required section: ${section}\n"
  fi
done

if [[ -n "$ERRORS" ]]; then
  MSG=$(echo -e "$ERRORS" | head -10)
  echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"additionalContext\":\"SKILL TEMPLATE VIOLATION in ${FILE}:\n${MSG}\nRequired: frontmatter (name, description, version, origin, triggers) + sections (When to Use, When NOT to Use). Fix before writing.\"}}"
  exit 0
fi

exit 0
