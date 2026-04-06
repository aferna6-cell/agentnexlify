#!/usr/bin/env bash
# Installs git hooks for AgentNexLiFy development
# Run once after cloning: bash scripts/install-hooks.sh

set -e

HOOK_DIR=".git/hooks"
SCRIPT_DIR="scripts/hooks"

echo "Installing AgentNexLiFy git hooks..."

if [ ! -d "$HOOK_DIR" ]; then
    echo "Error: .git/hooks directory not found. Are you in the repo root?"
    exit 1
fi

# Install pre-commit hook
if [ -f "$SCRIPT_DIR/pre-commit" ]; then
    cp "$SCRIPT_DIR/pre-commit" "$HOOK_DIR/pre-commit"
    chmod +x "$HOOK_DIR/pre-commit"
    echo "  Installed pre-commit hook"
fi

# Install pre-push hook
if [ -f "$SCRIPT_DIR/pre-push" ]; then
    cp "$SCRIPT_DIR/pre-push" "$HOOK_DIR/pre-push"
    chmod +x "$HOOK_DIR/pre-push"
    echo "  Installed pre-push hook"
fi

echo ""
echo "Done. Hooks installed:"
echo "  pre-commit - blocks secrets, dangerous imports, weak JS/TS tests, .env files"
echo "  pre-push   - runs test-quality lint (JS/TS + Python), fast critical pytest subset, frontend build"
echo ""
echo "To bypass in an emergency: git commit/push --no-verify"
