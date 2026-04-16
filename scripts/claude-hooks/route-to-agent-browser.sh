#!/usr/bin/env bash
# PreToolUse hook for WebFetch|WebSearch.
# If agent-browser CLI is installed, deny the tool call and tell Claude to use agent-browser.
# If NOT installed, allow the original tool call to proceed (graceful fallback).
# Prevents the circular deadlock where hook forces a tool that doesn't exist.

set -euo pipefail

if command -v agent-browser >/dev/null 2>&1; then
  # Agent-browser is available — route Claude to it for richer browsing
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Use agent-browser via Bash instead","additionalContext":"BLOCKED: Use agent-browser CLI via Bash instead of WebFetch/WebSearch. agent-browser gives real browser rendering, JS execution, redirect handling. Commands: agent-browser open <url> | agent-browser text | agent-browser screenshot | agent-browser links | agent-browser click <sel> | agent-browser fill <sel> <text>"}}'
else
  # Agent-browser not installed — allow WebFetch/WebSearch to run natively
  # (do NOT deny; emit empty hookSpecificOutput so Claude Code runs the tool)
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"agent-browser CLI not installed; falling back to native WebFetch/WebSearch. Install via: npm install -g agent-browser"}}'
fi
