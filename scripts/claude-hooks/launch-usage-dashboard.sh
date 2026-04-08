#!/usr/bin/env bash
# Launch claude-usage dashboard if not already running
# SessionStart hook — runs silently in background

DASHBOARD_DIR="$HOME/claude-usage"
PORT=8080

# Skip if dashboard already running
if lsof -i :$PORT -sTCP:LISTEN >/dev/null 2>&1; then
  exit 0
fi

# Skip if repo missing
if [ ! -f "$DASHBOARD_DIR/cli.py" ]; then
  exit 0
fi

# Launch in background, detached from this shell
cd "$DASHBOARD_DIR"
nohup python3 cli.py dashboard >/dev/null 2>&1 &
disown

exit 0
