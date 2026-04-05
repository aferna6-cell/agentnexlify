#!/usr/bin/env bash
# KAIROS Daemon — Persistent background agent for AgentNexLiFy
# Memory consolidation, project monitoring, and dream reports.
#
# Usage:
#   ./daemon.sh start   — Start the daemon (nohup, background)
#   ./daemon.sh stop    — Stop the daemon
#   ./daemon.sh status  — Check if the daemon is running
#   ./daemon.sh run     — Run one cycle in the foreground (for testing)
#
# Configuration:
#   KAIROS_INTERVAL  — seconds between cycles (default: 1800 = 30 min)
#   KAIROS_REPO      — repo root (auto-detected from script location)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KAIROS_REPO="${KAIROS_REPO:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
KAIROS_INTERVAL="${KAIROS_INTERVAL:-1800}"
PID_FILE="/tmp/kairos.pid"
LOG_DIR="$KAIROS_REPO/docs/kairos"
LOG_FILE="$LOG_DIR/daemon.log"

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        else
            # Stale PID file — clean it up
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

do_start() {
    if is_running; then
        echo "KAIROS daemon is already running (PID $(cat "$PID_FILE"))."
        exit 0
    fi

    echo "Starting KAIROS daemon (interval: ${KAIROS_INTERVAL}s)..."
    log "=== KAIROS daemon starting (interval: ${KAIROS_INTERVAL}s) ==="

    nohup bash -c "
        echo \$\$ > \"$PID_FILE\"
        while true; do
            echo \"[$(date '+%Y-%m-%d %H:%M:%S')] --- Cycle start ---\" >> \"$LOG_FILE\"

            # Run autodream (memory consolidation)
            if python3 \"$SCRIPT_DIR/autodream.py\" >> \"$LOG_FILE\" 2>&1; then
                echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] autodream: OK\" >> \"$LOG_FILE\"
            else
                echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] autodream: FAILED (exit \$?)\" >> \"$LOG_FILE\"
            fi

            # Run monitor (project health)
            if python3 \"$SCRIPT_DIR/monitor.py\" >> \"$LOG_FILE\" 2>&1; then
                echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] monitor: OK\" >> \"$LOG_FILE\"
            else
                echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] monitor: FAILED (exit \$?)\" >> \"$LOG_FILE\"
            fi

            echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] --- Cycle complete. Sleeping ${KAIROS_INTERVAL}s ---\" >> \"$LOG_FILE\"
            sleep $KAIROS_INTERVAL
        done
    " >> "$LOG_FILE" 2>&1 &

    # Wait a moment for the PID file to be written
    sleep 1

    if is_running; then
        echo "KAIROS daemon started (PID $(cat "$PID_FILE"))."
        echo "Log: $LOG_FILE"
    else
        echo "ERROR: KAIROS daemon failed to start. Check $LOG_FILE"
        exit 1
    fi
}

do_stop() {
    if ! is_running; then
        echo "KAIROS daemon is not running."
        exit 0
    fi

    local pid
    pid=$(cat "$PID_FILE")
    echo "Stopping KAIROS daemon (PID $pid)..."
    log "=== KAIROS daemon stopping (PID $pid) ==="

    # Kill the process group to catch the sleep child too
    kill -- -"$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
    rm -f "$PID_FILE"

    echo "KAIROS daemon stopped."
    log "=== KAIROS daemon stopped ==="
}

do_status() {
    if is_running; then
        local pid
        pid=$(cat "$PID_FILE")
        echo "KAIROS daemon is RUNNING (PID $pid)."
        echo "Interval: ${KAIROS_INTERVAL}s"
        echo "Log: $LOG_FILE"

        # Show last 5 log lines
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "Recent log:"
            tail -5 "$LOG_FILE"
        fi

        # Show latest dream report if any
        local latest_dream
        latest_dream=$(ls -t "$LOG_DIR"/dream-*.md 2>/dev/null | head -1)
        if [ -n "$latest_dream" ]; then
            echo ""
            echo "Latest dream report: $latest_dream"
        fi

        # Show latest health report if any
        local latest_health
        latest_health=$(ls -t "$LOG_DIR"/health-*.md 2>/dev/null | head -1)
        if [ -n "$latest_health" ]; then
            echo "Latest health report: $latest_health"
        fi
    else
        echo "KAIROS daemon is NOT running."
    fi
}

do_run() {
    echo "Running one KAIROS cycle (foreground)..."
    log "=== Manual cycle start ==="

    echo "--- autodream ---"
    python3 "$SCRIPT_DIR/autodream.py" 2>&1 | tee -a "$LOG_FILE"

    echo ""
    echo "--- monitor ---"
    python3 "$SCRIPT_DIR/monitor.py" 2>&1 | tee -a "$LOG_FILE"

    log "=== Manual cycle complete ==="
    echo ""
    echo "Done. Reports written to $LOG_DIR/"
}

case "${1:-}" in
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    status)
        do_status
        ;;
    run)
        do_run
        ;;
    *)
        echo "Usage: $0 {start|stop|status|run}"
        echo ""
        echo "  start   — Start the background daemon"
        echo "  stop    — Stop the daemon"
        echo "  status  — Check if running + show recent output"
        echo "  run     — Run one cycle in the foreground"
        exit 1
        ;;
esac
