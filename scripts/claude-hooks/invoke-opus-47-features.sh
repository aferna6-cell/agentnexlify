#!/usr/bin/env bash
# UserPromptSubmit hook -- reminds Claude to leverage Opus 4.7 features
# Self-verification, /ultrareview, task budgets, 3x vision
# Cross-refs: .claude/rules/opus-4-7.md

set -euo pipefail

INPUT=$(cat /dev/stdin 2>/dev/null || echo '{}')
# Extract user_prompt without requiring jq (it isn't installed in all envs)
PROMPT=$(echo "$INPUT" | python3 -c "import sys,json;d=json.load(sys.stdin) if sys.stdin.readable() else {};print(d.get('user_prompt',d.get('prompt','')))" 2>/dev/null || echo '')
PROMPT_LOWER=$(echo "$PROMPT" | tr '[:upper:]' '[:lower:]')

# Triggers for feature-specific reminders
NEEDS_VERIFY=false
NEEDS_REVIEW=false
NEEDS_BUDGET=false
NEEDS_VISION=false

for p in "fix" "implement" "build" "refactor" "split" "extract" "migrate" "update" "change" "add" "write"; do
  if echo "$PROMPT_LOWER" | grep -qE "\b$p\b"; then NEEDS_VERIFY=true; break; fi
done

for p in "ship" "merge" "pr" "pull request" "deploy" "release" "push to main" "review"; do
  if echo "$PROMPT_LOWER" | grep -qE "\b$p\b"; then NEEDS_REVIEW=true; break; fi
done

for p in "nightly" "cron" "background" "loop" "batch" "every" "daily" "hourly" "long-running" "autonomous"; do
  if echo "$PROMPT_LOWER" | grep -qE "\b$p\b"; then NEEDS_BUDGET=true; break; fi
done

for p in "screenshot" "image" "diagram" "design" "figma" "mockup" "pdf" "chart" "visual"; do
  if echo "$PROMPT_LOWER" | grep -qE "\b$p\b"; then NEEDS_VISION=true; break; fi
done

MSG="OPUS 4.7 FEATURES -- Model: claude-opus-4-7. Default effort: xhigh (new level between high and max)."

if [ "$NEEDS_VERIFY" = true ]; then
  MSG="$MSG | SELF-VERIFICATION: Before reporting done, state \"Verified: <what you checked> -- <PASS/FAIL>\". See rules/self-verification.md."
fi

if [ "$NEEDS_REVIEW" = true ]; then
  MSG="$MSG | /ultrareview: For any PR-ready change, invoke /ultrareview before merge. See rules/ultrareview.md."
fi

if [ "$NEEDS_BUDGET" = true ]; then
  MSG="$MSG | TASK BUDGETS: Long-running work needs a token cap. See rules/task-budgets.md."
fi

if [ "$NEEDS_VISION" = true ]; then
  MSG="$MSG | 3x VISION: Opus 4.7 accepts 2,576px images (3.75MP). Don't downsample unless cost matters. See rules/vision-3x.md."
fi

MSG="$MSG | FILL-INSTRUCTIONS-FIRST: If the rule/hook/plan you're following is missing, ambiguous, or wrong -- stop and fix the instruction before executing. See rules/fill-instructions-before-guessing.md."

# Emit as hookSpecificOutput so it prepends to prompt context
# JSON-escape via python (jq not always installed)
ESCAPED=$(printf '%s' "$MSG" | python3 -c "import sys,json;print(json.dumps(sys.stdin.read()))" 2>/dev/null || printf '"%s"' "$MSG")
printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":%s}}\n' "$ESCAPED"
