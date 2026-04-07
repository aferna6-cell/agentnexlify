#!/usr/bin/env bash
# Stop hook — fires when Claude finishes responding and is waiting for user input.
# This is the "Claude needs input" notification from the hooks guide.

# Drain stdin
cat < /dev/stdin > /dev/null 2>&1

TITLE="AgentNexLiFy"
MESSAGE="Claude finished — waiting for input"

OS=$(uname -s)
case "$OS" in
    Linux)
        if command -v notify-send &>/dev/null; then
            notify-send "$TITLE" "$MESSAGE" --urgency=normal 2>/dev/null
        elif command -v powershell.exe &>/dev/null; then
            powershell.exe -WindowStyle Hidden -Command "
                Add-Type -AssemblyName System.Windows.Forms;
                \$n = New-Object System.Windows.Forms.NotifyIcon;
                \$n.Icon = [System.Drawing.SystemIcons]::Information;
                \$n.Visible = \$true;
                \$n.ShowBalloonTip(4000, '$TITLE', '$MESSAGE', 'Info');
                Start-Sleep -Seconds 5;
                \$n.Dispose()
            " 2>/dev/null &
        else
            printf "\a"
        fi
        ;;
    Darwin)
        osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\"" 2>/dev/null
        ;;
    *)
        printf "\a"
        ;;
esac

exit 0
