# Morning Digest — 2026-07-23

Generated: 2026-07-23 UTC | 6 commits last 24h

---

## Commits (last 24h)

- `94e3c1a` ops: nightly-commit-review 2026-07-23 [auto-nightly]
- `281156f` Docs: record first MCP tenant activation [skip ci] (#564)
- `970da66` Round 8: approval-loop repair — dedupe guard, name fallback, funnel meters [skip ci] (#563)
- `0e98b72` Fix MCP mount behind Railway proxy: disable DNS-rebinding host allowlist [skip ci] (#562)
- `e646bdc` Round 7: stage-3 plan gate, audit batch, calls.py split, owner MCP server, suite onboarding (#561)
- `c9654d0` ops: morning-digest 2026-07-22

**Notable:** Owner MCP server is live (`/mcp`). First MCP tenant activated (#564 doc commit). calls.py god-file split 1196 → 237+875+133 lines. DNS-rebinding fix for Railway proxy. Approval-loop dedupe guard in (#563).

---

## Issues Updated (last 24h)

- **#413** ACTION REQUIRED: Activate referral reward | ✅ CLOSED (2026-07-22) — resolved
- **#558** fix: require_agent_os_access missing from 10 os_* routers (H1 security audit) | OPEN — needs review/merge
- **#399** autopilot-issue-loop — AUTOPILOT_GH_TOKEN expired [CRITICAL] | OPEN — Day 17+, unresolved
- **#403** Set ANTHROPIC_API_KEY in GitHub Actions secrets | OPEN — blocking KB autopopulate
- **#560** Morning digest 2026-07-22 | OPEN

---

## Open PRs Needing Action

- **#565** subconscious: run 100 — Step 9G: KB autopopulate self-healing trigger | draft | 0 days old (today)
- **#559** subconscious: run 100 — Fix Agent OS plan gate coverage gap (H1) | draft | 1 day old
- **#537** subconscious: runs 100+101 — Wire MCP client + Fix Step 9F execution gap | draft | 2 days old
- **#521** feat(ops-automation): pending_automations retry worker (#118) | draft | 2 days old
- **#517** feat(ops-automation): migration 180 — pending_automations + activity_feed_events (#114) | draft | 2 days old
- **#509** docs: update current-tasks with run 99 status | draft | 3 days old
- **#487** chore(deps): bump actions/github-script 7→9 | **open (not draft)** | 3 days old
- **#488** chore(deps): bump actions/setup-node 4→7 | **open** | 3 days old
- **#489** chore(deps): bump actions/cache 4→6 | **open** | 3 days old
- **#490** chore(deps): bump actions/setup-python 5→7 | **open** | 3 days old

**Draft pile growing:** 6 draft PRs from subconscious + ops-automation, some 2-3 days old. Need review or merge.
**Dependabot PRs (#487-490):** 4 non-draft bumps sitting unreviewed for 3 days.

---

## Subconscious Recommendation (Run 99 / 2026-07-20)

Step 9F (KB Autopopulate Staleness Check) implemented directly after 3 consecutive carry-forward cycles. Block written to `.claude/skills/nightly-commit-review/SKILL.md`. New PR #565 today proposes Step 9G (self-healing trigger). Run 100 mandate: confirm Step 9F fires in today's nightly log, check GH #399 still blocking.

**KB status: STALE — last run 2026-07-13, 10 days ago.** Past 7-day threshold. Step 9F in today's nightly should have commented on #403. Root cause: ANTHROPIC_API_KEY missing from Actions secrets (#403).

---

## Top 3 Priorities Today

1. **Rotate AUTOPILOT_GH_TOKEN (GH #399) — Day 17, CRITICAL.** Unblocks autopilot issue-to-PR loop and 30+ queued ai-ready issues. Token expired in GitHub Actions. Owner action: generate new PAT, store as `AUTOPILOT_GH_TOKEN` in repo secrets.

2. **Review + merge PR for GH #558 — H1 security finding.** `require_agent_os_access` missing from 10 `os_*` routers. Agent OS plan gating is incomplete. PR is open, nightly classified as MEDIUM, needs human eyes before merge.

3. **Fix KB autopopulate (GH #403) — 10 days stale.** Add `ANTHROPIC_API_KEY` to GitHub Actions secrets. KB is blind to new competitor/AI/vertical intel. Run `bash scripts/daily/kb-autopopulate.sh` manually to catch up while Actions is fixed.

**Bonus quick win:** Merge the 4 Dependabot bumps (#487-490) — routine CI dep bumps, low risk, 3 days old.

---

*Nightly review today: clean cycle, all MEDIUM commits well-tested, 0 bugs auto-fixed, 0 issues filed.*
