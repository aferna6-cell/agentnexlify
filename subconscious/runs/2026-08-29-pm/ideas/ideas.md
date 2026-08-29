# Ideas — Run 112 (2026-08-29-pm)

## Evidence Digest

3-day git window: no production code changes — all ops/nightly + subconscious commits. Zero production feature activity.

Key signals:
- **Step 9J 0% effectiveness**: 2 consecutive nightlies (2026-08-28, 2026-08-29) — 10+ Dependabot PRs, all `mergeable_state: unknown`, 0 merged. Run 111 did not implement rebase fix despite "1st carry-forward autonomous-executable" designation.
- **2nd consecutive carry-forward fire**: Run 110 (recommendation) + Run 111 (claimed 1st carry-forward) both failed to deliver the autonomous implementation. Governance precedent: Step 9I (1st carry → direct implementation, run 107), Step 9J initial add (1st carry → direct, run 109).
- **CVE window**: 20+ Dependabot PRs aging (oldest #594). 2-3 week security gap grows daily.
- **GH #669 stalled 9d+**: 95 routers missing block_demo_role. Loop stalled (GH #399 Day 57+). 3 ai-ready issues blocked.
- **Brain connector 37d stale**: GH #684 open, SUPABASE_ACCESS_TOKEN not set. Step 9C fires daily warning but human hasn't acted in 37 days.
- **Recent fixes** (last 7d): decc1e9 (appointment confirmation for non-existent appts), #677 (managed-agents audit 7 findings), #682/#680 (CI workflow unscheduling).

---

### Idea 1: Implement Step 9J @dependabot rebase trigger (2nd carry-forward — AUTONOMOUS-EXECUTABLE)
**Evidence:** nightly-2026-08-28 + nightly-2026-08-29 both confirmed `mergeable_state: unknown` for all 10+ Dependabot PRs, 0 merged. Run 111 designated as "1st carry-forward autonomous-executable" but remained a recommendation. Run 112 is the 2nd consecutive carry-forward — governance mandates direct implementation per established precedent (Steps 9I, 9J initial add). Full implementation sketch in subconscious/runs/2026-08-28/winning-concept.md. 10-15 line SKILL.md edit.
**Action:** Edit Step 9J block in `.claude/skills/nightly-commit-review/SKILL.md`: after `mergeable_state != "clean" → skip`, add branch for `state == "unknown"`: list PR comments, check for existing @dependabot rebase <48h (dedup), post "@dependabot rebase" via mcp__github__add_issue_comment if absent, cap at 5 per run, log "rebase-triggered" count.
**Impact:** Step 9J goes from 0% → ~80% effective within 24-48h. 20+ aging Dependabot PRs begin resolving. CVE window shrinks to <24h after CI passes. Compounds permanently — all future unknown-state PRs handled.
**Category:** workflow

---

### Idea 2: Step 9K — Stale subconscious draft PR report in nightly-commit-review
**Evidence:** governance.json run_111_mandate explicitly named Step 9K as candidate "if subconscious PRs still >=3 open." 22 run directories exist. Prior runs noted "5 subconscious draft PRs open" accumulating over months. Each subconscious run that opens a PR and never closes it wastes GitHub UI space and creates confusion. Morning digest 2026-08-28 did not mention any subconscious PR closures.
**Action:** Add Step 9K block to `.claude/skills/nightly-commit-review/SKILL.md`: list open PRs with head branch containing "subconscious", report count and age, flag any >30 days old as stale, log result.
**Impact:** Operational visibility on PR accumulation. Report-only (no auto-close) — zero risk. Informs human about when to clean up stale draft PRs. Same S-effort channel as Steps 9F-9J.
**Category:** operational

---

### Idea 3: Post GH #669 middleware implementation sketch (class-wide block_demo_role)
**Evidence:** GH #669 (9d+, ai-ready) tracks 95 routers missing block_demo_role. Loop stalled (GH #399 Day 57+). nightly-2026-08-29 Step 9I confirmed: 30+ files scanned, all violations already tracked by #669, 0 new issues. Step 9I found all, but no fix mechanism exists while loop is down. Idea: post an implementation sketch comment on GH #669 that proposes a FastAPI middleware approach (adds the guard globally rather than per-route).
**Action:** Add a comment on GH #669 with: (1) middleware code snippet for FastAPI lifespan that applies block_demo_role globally to all mutating routes, (2) exact file path (`backend/main.py` middleware registration), (3) test pattern. Marks issue as "ready-to-implement without autopilot" for human pickup.
**Impact:** Unblocks GH #669 from loop dependency. Human can implement in 30 min without needing to read 95 router files. Closes entire class of block_demo_role misses permanently.
**Category:** code_health

---

### Idea 4: Add managed-agents telemetry step to nightly (Step 9L candidate)
**Evidence:** PR #677 (2026-08-21) fixed 7 managed-agents audit findings. decc1e9 fixed appointment confirmation for non-existent appointments. Active managed-agents work with no visibility dashboard. Morning digests mention managed agents but no daily health check. bug-patterns.md shows silent-green automation caused 5-week outage for Keys Koffee — same class risk exists for managed agent sessions.
**Action:** Add Step 9L block to nightly SKILL.md: query managed_agents session table (or health endpoint /api/admin/loop-health from PR admin_loop_health.py) for sessions with >5 errors in last 24h; log count; file GH issue if >10 error sessions (labels: operational, ai-ready).
**Impact:** Catches managed-agent failures within 24h vs weeks of silence. Same pattern as Step 9B (healthz monitor) but for AI sessions specifically.
**Category:** operational

---

### Idea 5: File implementation-ready comment on GH #684 (brain connector SUPABASE_ACCESS_TOKEN)
**Evidence:** GH #684 open for 4d+ (opened 2026-08-25). Brain connector 37 days stale. SUPABASE_ACCESS_TOKEN not set in Railway. nightly Step 9C fires warning every night (Day 37 warning posted today). 6 prior warnings escalated with no action. Bonus action: posting a comment with exact setup path. The run 111 winning-concept.md already listed this as "Bonus Action." This idea promotes it to standalone candidate.
**Action:** Post a comment on GH #684 with exact Railway → Variables → SUPABASE_ACCESS_TOKEN setup steps including where to find the token value in Supabase dashboard (Settings → Access Tokens → Create new). Include brain connector impact: knowledge-base compile, KB-driven AI answers, Step 9E tracking.
**Impact:** Reduces SUPABASE_ACCESS_TOKEN setup friction from "unclear" to "copy-paste." 2-minute human action vs indefinite delay. Brain connector at 37d — longest staleness in history.
**Category:** operational
