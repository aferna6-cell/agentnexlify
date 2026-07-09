# Improvement Backlog — 2026-07-07-pm (Run 82)

## Active
- **KB autopopulate → GitHub Actions workflow** (run 82 winner): Create `.github/workflows/kb-autopopulate.yml`, schedule `0 6,18 * * *`, use `claude --print` headless with `ANTHROPIC_API_KEY` secret. Restores twice-daily KB growth after 63-day silent gap. `autonomous_executable: true`.

## Parking Lot (survived debate, not chosen this run)

- **Add `brain/INGESTION-LOG.md` to Phase 2 evidence in SKILL.md** (idea 2): One-line addition to the "Also read:" block. Low effort, compounds across all future runs. Deferred per mandate: "after GH #394 resolved" (brain connectors still failing). Implement in run 83 or alongside KB workflow. Autonomous-executable.

- **Subconscious Phase 2 prior-winner verification step** (idea 4): Add MCP check for `ai-ready` label presence on the prior winner's GH issue before declaring "autonomous-executed" in governance. Prevents false-positive status in morning digest. Medium effort, addresses an edge case that only fires when nightly runs before the same-day subconscious. Revisit if false-positives recur.

- **Lead source analytics dashboard** (idea 5): Wire existing `leads.lead_source` column to a Recharts pie/bar chart on the Leads dashboard page. Low-effort frontend feature closing a cross-industry customer gap. Blocked this run: pending_approvals budget would overflow (pending #385 PR + #107 would already be at limit). Target: run 83 or 84 after pending items clear.

## Rejected This Run

- **Activate issue-to-pr-loop for Zapier plan_status bug #107** (idea 3): WEAKENED in debate. Timing issue: #385 ai-ready label pending tonight's nightly → pending_approvals=1 → adding #107 hits max=2. Two simultaneous MEDIUM-risk backend PRs in flight before human review contradicts the purpose of the moratorium cap. Revisit in run 83 after #385 PR is opened and merged; pending_approvals will return to 0.

## Questions for Next Run (Run 83)

1. Did tonight's nightly (2026-07-07/08 at 2:37 AM) successfully apply `ai-ready` label to GH #385? Verify via `mcp__github__issue_read` — labels should include `ai-ready`.
2. Did the issue-to-pr-loop open a PR for GH #385 SMS Compliance Dashboard? Check open PRs for a new draft since this run.
3. Has GH #394 (brain connector credentials) received human action? Check issue comments and INGESTION-LOG.md — if GitHub 403 is resolved, INGESTION-LOG.md will show a successful refresh.
4. Was the KB autopopulate GH Actions workflow (`kb-autopopulate.yml`) merged and did its first run succeed? Check `knowledge-base/log.md` for entries after 2026-07-07.
5. If #385 PR is merged: pending_approvals=0 → Zapier #107 ai-ready label is now safe to recommend (idea 3 revival).
