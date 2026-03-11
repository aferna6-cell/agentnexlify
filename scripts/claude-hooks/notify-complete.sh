#!/usr/bin/env bash
# Notification hook — alerts when a background agent completes
# Works on Linux (WSL) with notify-send, macOS with osascript

INPUT=$(cat)

# Extract tool name from JSON input
TOOL_NAME=$(echo "$INPUT" | grep -oP '"tool_name"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')

# Only notify for agent completions
case "$TOOL_NAME" in
    *Agent*|*Task*)
        ;;
    *)
        exit 0
        ;;
esac

MESSAGE="Agent task completed"

# Detect OS and send notification
OS=$(uname -s)
case "$OS" in
    Linux)
        if command -v notify-send &> /dev/null; then
            notify-send "AgentNexLiFy" "$MESSAGE" --icon=dialog-information 2>/dev/null
        elif command -v powershell.exe &> /dev/null; then
            powershell.exe -Command "
                [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null;
                \$notify = New-Object System.Windows.Forms.NotifyIcon;
                \$notify.Icon = [System.Drawing.SystemIcons]::Information;
                \$notify.Visible = \$true;
                \$notify.ShowBalloonTip(5000, 'AgentNexLiFy', '$MESSAGE', 'Info');
                Start-Sleep -Seconds 6;
                \$notify.Dispose()
            " 2>/dev/null &
        else
            echo -e "\a"
        fi
        ;;
    Darwin)
        osascript -e "display notification \"$MESSAGE\" with title \"AgentNexLiFy\"" 2>/dev/null
        ;;
    *)
        echo -e "\a"
        ;;
esac

exit 0
