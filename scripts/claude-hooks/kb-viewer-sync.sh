#!/bin/bash
# Auto-regenerate viewer-data.json when wiki articles are saved.
# Triggered by PostToolUse Write|Edit and FileChanged hooks.
# Reads CLAUDE_TOOL_INPUT to check if the file is inside knowledge-base/wiki/.

INPUT="${CLAUDE_TOOL_INPUT:-}"
FILE_PATH=""

# Extract file_path from JSON input (handles both Write and Edit tools)
if echo "$INPUT" | grep -q '"file_path"'; then
  FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('file_path',''))" 2>/dev/null)
fi

# Also check FILE_PATH env var (FileChanged hook)
if [ -z "$FILE_PATH" ] && [ -n "${FILE_PATH:-}" ]; then
  FILE_PATH="${FILE_PATH}"
fi

# Only regenerate for wiki markdown files
if echo "$FILE_PATH" | grep -q "knowledge-base/wiki.*\.md$"; then
  # Run regenerator quietly; log errors only
  cd /home/aidan/agentnexlify 2>/dev/null || true
  if python3 knowledge-base/viewer-data-generator.py > /dev/null 2>&1; then
    echo '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"viewer-data.json regenerated (wiki article updated)"}}'
  fi
fi
