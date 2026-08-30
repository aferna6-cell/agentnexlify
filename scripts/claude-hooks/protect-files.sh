#!/usr/bin/env bash
# Block edits to sensitive/protected files
# Enhances the existing pre-edit-check.sh with a broader file list

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | grep -oP '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"file_path"\s*:\s*"//;s/"//')

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Hard blocks (exit 2 = blocked)
case "$FILE_PATH" in
    *.env|*.env.*)
        echo "BLOCKED: Do not edit .env files. Set environment variables in Railway/Vercel directly." >&2
        exit 2
        ;;
    *.pem|*.key|*.crt)
        echo "BLOCKED: Do not edit certificate/key files via Claude." >&2
        exit 2
        ;;
    *secrets/*|*credentials*)
        echo "BLOCKED: Do not edit secrets files via Claude." >&2
        exit 2
        ;;
    .git/*)
        echo "BLOCKED: Do not edit .git internals directly." >&2
        exit 2
        ;;
    package-lock.json|yarn.lock)
        echo "BLOCKED: Do not edit lock files directly. Run npm install or yarn instead." >&2
        exit 2
        ;;
esac

# Soft warnings (exit 0 = allowed but noted). Notes go to stderr: some hook
# runners (e.g. Cursor) parse stdout as JSON and fail closed on plain text,
# which would turn these allow-with-note paths into hard blocks.
case "$FILE_PATH" in
    migrations/*.sql)
        if [ -f "$FILE_PATH" ]; then
            echo "WARNING: Editing an existing migration. Existing migrations should be immutable. Create a new numbered migration instead." >&2
        fi
        ;;
    *main.py)
        echo "NOTE: main.py contains CORS config and router registration. Verify both after editing." >&2
        ;;
    *settings.json)
        echo "NOTE: Editing Claude Code settings. Verify hook paths are correct." >&2
        ;;
    widget/agentnexlify-widget.js|frontend/public/widget/agentnexlify-widget.js)
        echo "REMINDER: Widget files must be kept in sync. Edit both widget/ and frontend/public/widget/." >&2
        ;;
esac

exit 0
