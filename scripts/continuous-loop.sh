#!/usr/bin/env bash
# =============================================================================
# Universal Continuous Development Loop
# Point it at any repo. It runs forever.
# Usage: bash continuous-loop.sh /path/to/repo
# =============================================================================

set -e

# Validate input
if [ -z "$1" ]; then
    echo "Usage: bash continuous-loop.sh /path/to/repo"
    echo ""
    echo "Example: bash continuous-loop.sh ~/agentnexlify"
    echo "Example: bash continuous-loop.sh ~/other-project"
    exit 1
fi

REPO_DIR="$(cd "$1" && pwd)"
cd "$REPO_DIR"

# Verify it's a git repo
if [ ! -d ".git" ]; then
    echo "ERROR: $REPO_DIR is not a git repository."
    exit 1
fi

# Setup
COMMS_DIR="$REPO_DIR/.claude/agent-comms"
LOOP_LOG="$COMMS_DIR/loop-log.md"
LOOP_PROMPT="$COMMS_DIR/loop-prompt.md"
BACKLOG="$COMMS_DIR/backlog.md"
SESSION_COUNT=0

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

REPO_NAME=$(basename "$REPO_DIR")

echo -e "${CYAN}==========================================${NC}"
echo -e "${CYAN}  Continuous Loop: ${GREEN}$REPO_NAME${NC}"
echo -e "${CYAN}==========================================${NC}"
echo -e "Path:    ${GREEN}$REPO_DIR${NC}"
echo -e "Backlog: ${GREEN}$BACKLOG${NC}"
echo -e "Log:     ${GREEN}$LOOP_LOG${NC}"
echo -e "Stop:    ${YELLOW}Ctrl+C${NC}"
echo ""

mkdir -p "$COMMS_DIR"

# Check loop prompt exists
if [ ! -f "$LOOP_PROMPT" ]; then
    echo -e "${YELLOW}Loop prompt not found at $LOOP_PROMPT${NC}"
    echo -e "Run the setup first: paste the loop prompt into Claude Code."
    exit 1
fi

# Check backlog exists, create skeleton if not
if [ ! -f "$BACKLOG" ]; then
    cat > "$BACKLOG" << 'EOF'
# Work Backlog

Add tasks here. The loop works through them in priority order.

## Features (build these)

- [ ] Example: Add webhook test endpoint

## Bugs (fix these)

- [ ] Example: Widget not capturing phone numbers

## Tests (write these)

- [ ] Example: Test signup flow end-to-end

## Content (generate these)

- [ ] Example: Write onboarding email sequence

---

_The loop reads this file every cycle and picks the highest-priority incomplete task._
EOF
    echo -e "${GREEN}Created backlog skeleton at $BACKLOG${NC}"
    echo -e "${YELLOW}Add your tasks before starting the loop.${NC}"
    echo ""
fi

# Resume info
if [ -f "$LOOP_LOG" ]; then
    TOTAL_CYCLES=$(grep -c "^## Cycle" "$LOOP_LOG" 2>/dev/null || echo "0")
    echo -e "Resuming from cycle ${GREEN}$TOTAL_CYCLES${NC}"
fi

# Trap Ctrl+C
cleanup() {
    echo ""
    echo -e "${YELLOW}Loop stopped.${NC}"
    echo -e "Sessions: ${GREEN}$SESSION_COUNT${NC}"
    echo -e "Resume:   ${GREEN}bash continuous-loop.sh $REPO_DIR${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# The infinite loop
while true; do
    SESSION_COUNT=$((SESSION_COUNT + 1))
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

    echo ""
    echo -e "${CYAN}--- $REPO_NAME | Session $SESSION_COUNT | $TIMESTAMP ---${NC}"
    echo ""

    git pull --rebase 2>/dev/null || true

    # Build context for Claude
    RESUME_CTX=""
    [ -f "$COMMS_DIR/checkpoint.md" ] && RESUME_CTX="Read .claude/agent-comms/checkpoint.md to restore state from the previous session. "
    [ -f "$LOOP_LOG" ] && RESUME_CTX="${RESUME_CTX}Read .claude/agent-comms/loop-log.md for history. Do not redo completed work. "

    claude -p "
${RESUME_CTX}You are in the continuous development loop. Read .claude/agent-comms/loop-prompt.md for your full instructions. Read .claude/agent-comms/backlog.md for the work queue. Begin with STEP 1.
" \
    --allowedTools "Read" "Write" "Edit" "MultiEdit" "Glob" "Grep" "LS" \
    "Bash(git log*)" "Bash(git add*)" "Bash(git commit*)" "Bash(git push*)" "Bash(git pull*)" "Bash(git diff*)" "Bash(git status*)" "Bash(git stash*)" "Bash(git checkout -- *)" \
    "Bash(grep*)" "Bash(find*)" "Bash(wc*)" "Bash(cat*)" "Bash(ls*)" "Bash(head*)" "Bash(tail*)" "Bash(sort*)" "Bash(date*)" "Bash(echo*)" "Bash(chmod*)" "Bash(mkdir*)" "Bash(cp*)" "Bash(mv*)" \
    "Bash(npm run*)" "Bash(npm test*)" "Bash(npx*)" \
    "Bash(python -c*)" "Bash(python -m*)" "Bash(pytest*)" \
    "Bash(claude mcp*)" \
    "Agent" "Task" \
    --disallowedTools "Bash(rm -rf*)" "Bash(sudo*)" "Bash(curl*)" "Bash(wget*)" "Bash(pip install*)" "Bash(npm install --save*)" \
    --max-turns 200

    echo ""
    echo -e "${YELLOW}Session ended. Restarting in 15 seconds...${NC}"
    sleep 15
done
