#!/usr/bin/env bash
# UserPromptSubmit hook — triggers extended thinking for architecture, bugs, complex problems
set -euo pipefail

INPUT=$(cat /dev/stdin 2>/dev/null || echo '{}')
PROMPT=$(echo "$INPUT" | jq -r '.user_prompt // .prompt // empty' 2>/dev/null || echo '')

# Check if prompt matches high-complexity patterns
PROMPT_LOWER=$(echo "$PROMPT" | tr '[:upper:]' '[:lower:]')

MATCH=false
for pattern in "architect" "design" "refactor" "migration" "security" "debug" "bug" "broken" "failing" "crash" "error" "complex" "scalab" "performance" "tradeoff" "trade-off" "decision" "council" "strategy" "plan" "rethink" "redesign" "schema change" "breaking change" "rls" "auth" "payment" "stripe" "deploy" "production" "critical"; do
  if echo "$PROMPT_LOWER" | grep -q "$pattern"; then
    MATCH=true
    break
  fi
done

if [ "$MATCH" = true ]; then
  echo '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"ULTRATHINK ACTIVATED: This prompt touches architecture, debugging, security, or complex decisions. Use extended thinking. Break into subproblems. Consider 2-3 approaches. Think about edge cases, failure modes, and second-order effects. Plan before acting. Do NOT skip the thinking step."}}'
fi

exit 0
