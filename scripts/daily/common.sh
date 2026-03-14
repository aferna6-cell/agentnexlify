#!/usr/bin/env bash
# Shared helpers for the scheduled morning/evening routines.

set -euo pipefail

daily_date() {
    date '+%Y-%m-%d'
}

log_line() {
    local log_file="$1"
    shift
    printf '[%s] %s\n' "$(date '+%a %b %d %H:%M:%S %Z %Y')" "$*" >> "$log_file"
}

resolve_claude_bin() {
    if [ -n "${AGENTNEXLIFY_CLAUDE_BIN:-}" ]; then
        if [ -x "${AGENTNEXLIFY_CLAUDE_BIN}" ]; then
            printf '%s\n' "${AGENTNEXLIFY_CLAUDE_BIN}"
            return 0
        fi
        if command -v "${AGENTNEXLIFY_CLAUDE_BIN}" >/dev/null 2>&1; then
            command -v "${AGENTNEXLIFY_CLAUDE_BIN}"
            return 0
        fi
    fi

    if command -v claude >/dev/null 2>&1; then
        command -v claude
        return 0
    fi

    return 1
}

ensure_claude_bin() {
    local log_file="$1"
    local cli_bin
    if ! cli_bin="$(resolve_claude_bin)"; then
        log_line "$log_file" "ERROR: Claude CLI not found. Install @anthropic-ai/claude-code or set AGENTNEXLIFY_CLAUDE_BIN."
        return 1
    fi

    printf '%s\n' "$cli_bin"
}

git_pull_if_clean() {
    local log_file="$1"
    if ! git diff --quiet || ! git diff --cached --quiet; then
        log_line "$log_file" "Skipping git pull: worktree has uncommitted changes."
        return 0
    fi

    if git pull --rebase >> "$log_file" 2>&1; then
        log_line "$log_file" "git pull --rebase completed."
    else
        log_line "$log_file" "Git pull failed, continuing with local state."
    fi
}

log_exit_status() {
    local log_file="$1"
    local label="$2"
    local exit_code="$3"
    if [ "$exit_code" -eq 0 ]; then
        log_line "$log_file" "$label completed successfully."
    else
        log_line "$log_file" "$label failed with exit code $exit_code."
    fi
}
