#!/usr/bin/env bash
# UserPromptSubmit hook — check knowledge base before every prompt
set -euo pipefail

KB_INDEX="/home/aidan/agentnexlify/knowledge-base/INDEX.md"
KB_WIKI="/home/aidan/agentnexlify/knowledge-base/wiki"

# Only inject if KB exists and has content
if [ -f "$KB_INDEX" ] && [ -d "$KB_WIKI" ]; then
  ARTICLE_COUNT=$(find "$KB_WIKI" -name "*.md" -not -name "_*" 2>/dev/null | wc -l)
  if [ "$ARTICLE_COUNT" -gt 0 ]; then
    echo "{\"hookSpecificOutput\":{\"hookEventName\":\"UserPromptSubmit\",\"additionalContext\":\"KNOWLEDGE BASE CHECK: Before starting this task, check if knowledge-base/wiki/ has relevant articles ($ARTICLE_COUNT articles available). Read knowledge-base/INDEX.md for topics. Use existing knowledge before researching from scratch. After completing work that produces new knowledge, add it to the KB via /kb-ingest or by writing to knowledge-base/raw/.\"}}"
  fi
fi

exit 0
