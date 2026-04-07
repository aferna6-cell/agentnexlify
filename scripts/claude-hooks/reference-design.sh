#!/usr/bin/env bash
# PostToolUse hook on Write|Edit — reminds to reference design.md for frontend changes
set -euo pipefail

INPUT=$(cat /dev/stdin)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // .tool_response.filePath // empty')

# Only trigger for frontend files
if [[ -z "$FILE" ]] || [[ "$FILE" != *"frontend/"* ]]; then
  exit 0
fi

# Only for CSS, JSX, TSX, component files
if echo "$FILE" | grep -qE '\.(css|jsx|tsx|js)$'; then
  echo '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"DESIGN SYSTEM: You just modified a frontend file. Ensure your changes follow design.md in the project root. Key rules: accent=#00bfff, bg-card=#16161f, radius=10px/6px, font=Inter, dark theme default. Read design.md if unsure about any visual decision."}}'
fi

exit 0
