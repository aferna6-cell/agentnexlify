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
if echo "$FILE_PATH" | grep -qE "^backend/.*\.py$"; then
    if grep -q "lead" "$FILE_PATH" 2>/dev/null; then
        if grep -q "tenant_id" "$FILE_PATH" 2>/dev/null; then
            ISSUES="$ISSUES\nWARNING: Found 'tenant_id' in leads-related code in $FILE_PATH. The leads table uses 'client_id', not 'tenant_id'. Verify this is correct."
        fi
    fi
fi

# Check for lead_stage — column never existed, always use 'status' (CLAUDE.md invariant #2)
if [[ "$FILE_PATH" == *.py || "$FILE_PATH" == *.jsx || "$FILE_PATH" == *.js || "$FILE_PATH" == *.ts ]]; then
    if grep -qE "\blead_stage\b" "$FILE_PATH" 2>/dev/null; then
        ISSUES="$ISSUES\nCRITICAL: Found 'lead_stage' in $FILE_PATH. Column never existed — use 'status' instead (leads.status). This will cause a runtime 500."
    fi
fi

# Check for service_interest — column never existed, always use 'areas_of_interest' (CLAUDE.md invariant #3)
if [[ "$FILE_PATH" == *.py || "$FILE_PATH" == *.jsx || "$FILE_PATH" == *.js || "$FILE_PATH" == *.ts ]]; then
    if grep -qE "\bservice_interest\b" "$FILE_PATH" 2>/dev/null; then
        ISSUES="$ISSUES\nCRITICAL: Found 'service_interest' in $FILE_PATH. Column never existed — use 'areas_of_interest' instead. This will cause a runtime 500."
    fi
fi

# Widget byte-identical check (CLAUDE.md invariant #4)
WIDGET_SRC="widget/agentnexlify-widget.js"
WIDGET_DEST="frontend/public/widget/agentnexlify-widget.js"
if [[ "$FILE_PATH" == "$WIDGET_SRC" || "$FILE_PATH" == "$WIDGET_DEST" ]]; then
    if [ -f "$WIDGET_SRC" ] && [ -f "$WIDGET_DEST" ]; then
        if ! diff -q "$WIDGET_SRC" "$WIDGET_DEST" > /dev/null 2>&1; then
            if [[ "$FILE_PATH" == "$WIDGET_SRC" ]]; then
                COPY_CMD="cp $WIDGET_SRC $WIDGET_DEST"
            else
                COPY_CMD="cp $WIDGET_DEST $WIDGET_SRC"
            fi
            ISSUES="$ISSUES\nCRITICAL: Widget files are NOT byte-identical. Run: $COPY_CMD"
        fi
    fi
fi

# Check for retired model IDs (recurring bug — causes silent wrong-model usage)
if [[ "$FILE_PATH" == *.py || "$FILE_PATH" == *.jsx || "$FILE_PATH" == *.js || "$FILE_PATH" == *.ts ]]; then
    RETIRED=$(grep -nE "claude-opus-4-5|claude-opus-4-6|claude-sonnet-4-5|claude-opus-4-5-20250514" "$FILE_PATH" 2>/dev/null || true)
    if [ -n "$RETIRED" ]; then
        ISSUES="$ISSUES\nWARNING: Retired model ID in $FILE_PATH. Valid IDs: claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5-20251001. Found:\n$RETIRED"
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
