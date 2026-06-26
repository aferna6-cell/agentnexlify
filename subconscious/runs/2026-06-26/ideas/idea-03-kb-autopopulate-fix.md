# Idea 3: KB Autopopulate Fix (Replace agent-browser CLI with curl/WebFetch)

**Category:** operational
**Impact:** MEDIUM (KB stale 50+ days)
**Effort:** S (~15 min)
**Autonomous-executable:** YES

## Evidence
- KB stale ~50 days (kb-autopopulate.sh broken — agent-browser CLI not installed)
- Last KB compile: ~2026-05-05
- knowledge-base/INDEX.md likely reflects stale article set
- Parking lot ROI: 1.8 across runs 53-67
- council-onboarding-integration-2026-06-25 added a new article to brain/ — KB not capturing it

## Action
Edit `scripts/daily/kb-autopopulate.sh`:
1. Identify the `agent-browser` CLI call(s)
2. Replace with `curl -sL <url> | ...` or native WebFetch approach
3. Verify runs without the CLI installed

## Expected Impact
- KB resumes twice-daily compilation
- New articles from council sprint land in KB search
- ROI compounds: 50-day stale knowledge costs agents quality on every query

## Status
**PARKING LOT** — lower priority than check_project_invariants blocker. Run 69/70 candidate.
