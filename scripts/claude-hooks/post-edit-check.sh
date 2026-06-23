#!/usr/bin/env bash
# Claude Code post-edit hook
# Checks edited files for known dangerous patterns + CLAUDE.md invariants.
# Advisory only: prints WARNING/CRITICAL/REMINDER notes, always exits 0.

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

# Backend Python schema-discipline checks (CLAUDE.md invariants #1/#2/#3).
# Note: in [[ == ]] the '*' matches '/', so backend/*.py also matches subdir
# files like backend/services/foo.py — one pattern covers the whole tree.
if [[ "$FILE_PATH" == backend/*.py ]]; then
    # Invariant #1: leads/conversations use client_id, not tenant_id.
    if grep -q "lead" "$FILE_PATH" 2>/dev/null && grep -q "tenant_id" "$FILE_PATH" 2>/dev/null; then
        ISSUES="$ISSUES\nWARNING: Found 'tenant_id' in leads-related code in $FILE_PATH. The leads + conversations tables use 'client_id', not 'tenant_id'. Verify this is correct."
    fi
    # Invariant #2: lead status column is 'status', never 'lead_stage'.
    if grep -qw "lead_stage" "$FILE_PATH" 2>/dev/null; then
        ISSUES="$ISSUES\nWARNING: Found 'lead_stage' in $FILE_PATH. The leads status column is 'status' — 'lead_stage' never existed."
    fi
    # Invariant #3: leads service interest is 'areas_of_interest', never 'service_interest'.
    if grep -qw "service_interest" "$FILE_PATH" 2>/dev/null; then
        ISSUES="$ISSUES\nWARNING: Found 'service_interest' in $FILE_PATH. The leads column is 'areas_of_interest' — 'service_interest' never existed."
    fi
fi

# Retired / invalid Claude model IDs (.claude/rules/model-routing.md).
# Valid: claude-opus-4-7, claude-opus-4-6 (legacy-ok), claude-sonnet-4-6,
# claude-haiku-4-5-20251001. Flag clearly-retired families only — never flag 4-6/4-7.
if grep -qE "claude-opus-4-5|claude-opus-4-4|claude-sonnet-4-5|claude-haiku-4-[0-4]([^0-9]|$)|claude-3[.-]|claude-2[.-]" "$FILE_PATH" 2>/dev/null; then
    ISSUES="$ISSUES\nWARNING: Retired/invalid Claude model ID detected in $FILE_PATH. Valid IDs: claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5-20251001 (claude-opus-4-6 legacy-ok). See .claude/rules/model-routing.md."
fi

# Invariant #4: widget JS must stay byte-identical across all mirrors.
if [[ "$FILE_PATH" == *agentnexlify-widget.js ]]; then
    if command -v python3 >/dev/null 2>&1 && [ -f scripts/sync_widget_assets.py ]; then
        if ! python3 scripts/sync_widget_assets.py --check >/dev/null 2>&1; then
            ISSUES="$ISSUES\nCRITICAL: Widget assets are OUT OF SYNC after editing $FILE_PATH. Copy the change byte-identical to every mirror (widget/, frontend/public/widget/, landing-page-v2/widget/). Run: python3 scripts/sync_widget_assets.py --check"
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
