#!/usr/bin/env bash
# PreToolUse hook: warn when editing files that touch DB queries
# Reminds to check schema before writing queries

FILE_PATH="${CLAUDE_FILE_PATH:-}"

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Only trigger on backend Python files
case "$FILE_PATH" in
  */backend/routers/*.py|*/backend/services/*.py)
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"SCHEMA REMINDER: This file likely contains DB queries. Remember: leads/conversations use client_id (not tenant_id), status (not lead_stage), areas_of_interest (not service_interest). Use tenant_select()/tenant_table() helpers."}}'
    ;;
esac
