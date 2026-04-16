#!/usr/bin/env bash
# Sync canonical widget JS to widget/ directory.
# Run after any edit to frontend/public/widget/agentnexlify-widget.js
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CANONICAL="$REPO_ROOT/frontend/public/widget/agentnexlify-widget.js"
TARGET="$REPO_ROOT/widget/agentnexlify-widget.js"

if [ ! -f "$CANONICAL" ]; then
    echo "ERROR: canonical widget not found: $CANONICAL" >&2
    exit 1
fi

cp "$CANONICAL" "$TARGET"
echo "Synced $CANONICAL -> $TARGET"
