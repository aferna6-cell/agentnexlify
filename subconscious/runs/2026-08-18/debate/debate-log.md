# Debate Log — 2026-08-18 (Run 107)

Top 3 ideas by combined impact + evidence score:
1. Step 9I Carry-Forward (security, mandate-tracked, 1st carry → escalation imminent)
2. `dependabot-merge-runner` SKILL.md (workflow efficiency, strongest fresh evidence)
3. Step 9E Extension: alert on `unknown` last_rotated (operational, autonomous-executable channel)

---

## Idea 1: Step 9I — Nightly Demo-Role Security Sweep

### Challenge
- Nightly-2026-08-18 already manually ran the block_demo_role sweep this very run and found 100+ **pre-existing** gaps. A first-run Step 9I would fire on every one of those files — potentially 100+ duplicate GH issues filed in a single night, overwhelming the issue queue.
- The sweep is already happening manually inside nightly reviews. Automating it without dedup logic risks noise before signal.
- 1 carry-forward with no approval signal — the human may be intentionally deferring this.
- PR #653 (containing run 104-107 subconscious artifacts) still unapproved after 6 days; adding Step 9I here without approval risks another orphaned recommendation.

### Defend
- Step 9I has dedup logic in the implementation sketch: "check whether a GH issue is already open (search issues with label `security` and the filename)." Pre-existing files with open issues (#643, #661) would be skipped. The 100+ pre-existing gaps already have known issues or are candidates for GH issues; Step 9I files only when **no open issue exists**.
- The 1st carry is still within the governance window: autonomous-executable escalation fires at run **108**. The mandate tracks this explicitly.
- "New violation" scope is exactly correct — Step 9I catches `backend/routers/` files added AFTER the audit, not pre-existing ones. The skip-list (cache by filename) prevents re-firing on files already evaluated this week.
- Manual scanning is not sustainable. GH #643 (9 days) and GH #661 (2 days) both caught by humans reading nightly logs — that's the failure mode Step 9I closes.

### Verdict
**SURVIVES** — mandate-tracked, 1st carry, escalates to autonomous-executable at run 108. Dedup logic addresses the noise concern. Winner of the carry-forward track. If human approves before run 108, implement immediately; if not, SKILL.md edit fires autonomously at run 108 per governance precedent.

---

## Idea 2: `dependabot-merge-runner` SKILL.md

### Challenge
- Parking lot entry from run 106 backlog says: "Revisit when GH #399 (AUTOPILOT_GH_TOKEN) resolved and PR backlog grows past 10+." Current count is 5 (below 10), and GH #399 is still open (38+ days).
- A `dependabot-merge-runner` that calls `mcp__github__merge_pull_request` requires `AUTOPILOT_GH_TOKEN` — same blocker as issue-to-pr-loop. Building the skill without the token is a `PENDING_CREDENTIAL` ship.
- Fresh Dependabot PRs (#665/#666 at 1d) suggest the problem is self-healing slowly — new PRs merge faster than old ones pile up.
- Skill discovery 2026-08-17 proposed this but the same skill discovery already warned "parking lot" vs. immediate winner.

### Defend
- GH #399 blocks the **issue-to-pr-loop** for *product code PRs*, but the nightly-commit-review session likely uses the session-level GitHub token already authorized (the one that files GH issues via `mcp__github__*` right now). Evidence: nightly already calls `mcp__github__issue_write` for security issues without #399. Dependabot merges use `mcp__github__merge_pull_request` — same MCP server, same auth.
- The "10+ PRs" threshold from parking lot was advisory, not a hard condition. Evidence quality today: 5 PRs, 2 flagged daily in morning digest for 15 consecutive days, skill discovery "strong evidence" label.
- Pattern is accelerating: 2 new Dependabot PRs in 1 day (vs. 0 new the previous week). At this rate, 10+ threshold reached in ~5 more days.
- Building the SKILL.md now means the automation is ready the moment it's approved, regardless of token state. The skill can include a credential preflight check.

### Verdict
**SURVIVES but WEAKENED** — the token assumption needs validation and the parking lot threshold is a soft miss. This is a **strong parking lot candidate for fresh debate at run 108**, not the winner today. The skill discovery evidence is compelling but the dependency uncertainty and below-threshold PR count make `dependabot-merge-runner` the runner-up, not the winner.

---

## Idea 3: Step 9E Extension — Alert on `unknown` last_rotated Credentials

### Challenge
- Small scope change (one SKILL.md edit) to add `unknown` detection inside existing Step 9E — less headline impact than a whole new skill.
- SUPABASE_ACCESS_TOKEN is only one credential with `unknown` last_rotated. Filing a GH issue for a single known gap might be solved faster by just adding the human-readable reminder to the ops/credential-rotation-schedule.md notes column instead.
- Human has had the `unknown` row for 4 runs (runs 104-107) and hasn't filled it in. Adding a GH issue might just add another item to ignore.

### Defend
- The extension generalizes: any future credential added to `ops/credential-rotation-schedule.md` without a `last_rotated` date also surfaces automatically. It's not a one-off fix for SUPABASE_ACCESS_TOKEN; it's a class-level improvement to Step 9E.
- The filing trigger is "no open issue exists with the same title prefix" — it won't spam duplicate issues.
- **AUTONOMOUS-EXECUTABLE channel** applies: SKILL.md edit to an existing proven step (9E already implemented and running). This goes in immediately without human approval.
- Human ignoring a `last_rotated` date in a file is different from human ignoring a GH issue with `ops-reminder` label in the active issue queue. The GH issue escalates visibility to the human's daily workflow.

### Verdict
**SURVIVES — WINS AUTONOMOUS-EXECUTABLE SLOT** — small, high-certainty, autonomous-executable via proven SKILL.md channel. Implements this run without human approval. Closes a real gap (Step 9E can't protect credentials it doesn't know the age of).

---

## Synthesis

| Idea | Verdict | Track |
|------|---------|-------|
| Step 9I carry-forward | SURVIVES | Carry-forward, escalates run 108 |
| `dependabot-merge-runner` | WEAKENED → parking lot | Revisit run 108 |
| Step 9E unknown-token extension | SURVIVES → WINS autonomous slot | Implement this run |

**Winner:** Step 9E Extension — alert on `unknown` last_rotated credentials  
**Carry-forward active direction:** Step 9I (2nd carry, autonomous-executable at run 108)  
**Bonus (autonomous):** Post targeted comment on GH #403 with exact ANTHROPIC_API_KEY setup steps
