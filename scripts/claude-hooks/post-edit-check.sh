#!/usr/bin/env bash
# Claude Code post-edit hook
# Checks edited files for known dangerous patterns

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | grep -oP '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"file_path"\s*:\s*"//;s/"//')

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

ISSUES=""

# Check for __future__ annotations in router files
if [[ "$FILE_PATH" == *router*.py ]]; then
    if grep -q "from __future__ import annotations" "$FILE_PATH" 2>/dev/null; then
        ISSUES="$ISSUES\nCRITICAL: 'from __future__ import annotations' detected in $FILE_PATH. This WILL break all FastAPI request parsing. Remove it immediately."
    fi
fi

# Check for bare except blocks in Python files
if [[ "$FILE_PATH" == *.py ]]; then
    BARE=$(grep -n "except.*:.*pass\|except:$" "$FILE_PATH" 2>/dev/null || true)
    if [ -n "$BARE" ]; then
        ISSUES="$ISSUES\nWARNING: Bare except block in $FILE_PATH — this hides real errors. Add logging before the pass."
    fi
fi

# Check for hardcoded secrets
if grep -qE "sk_live_|sk_test_|sk-ant-" "$FILE_PATH" 2>/dev/null; then
    ISSUES="$ISSUES\nCRITICAL: Possible hardcoded API key detected in $FILE_PATH. Use environment variables instead."
fi

# Check for tenant_id in leads-related backend files (should be client_id for leads table)
if [[ "$FILE_PATH" == backend/*.py || "$FILE_PATH" == backend/**/*.py ]]; then
    if grep -q "lead" "$FILE_PATH" 2>/dev/null; then
        if grep -q "tenant_id" "$FILE_PATH" 2>/dev/null; then
            ISSUES="$ISSUES\nWARNING: Found 'tenant_id' in leads-related code in $FILE_PATH. The leads table uses 'client_id', not 'tenant_id'. Verify this is correct."
        fi
    fi
fi

# Remind to update schema-log if migration was created
if [[ "$FILE_PATH" == migrations/*.sql ]]; then
    ISSUES="$ISSUES\nREMINDER: You created/edited a migration. Update docs/dev-knowledge/schema-log.md with what changed and why."
fi

if [ -n "$ISSUES" ]; then
    echo -e "$ISSUES"
fi

exit 0
