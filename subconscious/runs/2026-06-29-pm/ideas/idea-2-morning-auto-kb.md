# Idea 2 — Add kb-autopopulate.sh to morning-auto.sh for Cloud Reliability

## Category
Operational

## Evidence
- kb-autopopulate.sh: currently scheduled via scripts/daily/morning-auto.sh (6am/6pm cron)
- Remote execution environment (this session is cloud-based)
- agent-browser CLI not installed in cloud container; requires WebFetch fallback
- Even after run 71 fix, cloud runs may hit the agent-browser path before falling to WebFetch
- morning-auto.sh is the authoritative daily scheduler

## Problem
kb-autopopulate.sh may continue to fail silently in cloud execution environments even after the run 71 fix if:
1. The script still tries agent-browser first and fails before hitting WebFetch fallback
2. Error handling swallows the agent-browser failure without surfacing it

## Recommendation
Add explicit cloud-detection to kb-autopopulate.sh: if agent-browser is not found in PATH, skip directly to WebFetch branch without attempting agent-browser. One additional line in the DISCOVER_PROMPT section.

Alternatively: add a `--skip-agent-browser` flag to kb-autopopulate.sh that morning-auto.sh can pass when it detects no agent-browser binary.

## Effort
S — 5-10 line change to kb-autopopulate.sh

## Risk
LOW — additive, doesn't break existing behavior when agent-browser IS present

## AUTONOMOUS-EXECUTABLE
YES — bash script edit, S effort, fully scripted change
