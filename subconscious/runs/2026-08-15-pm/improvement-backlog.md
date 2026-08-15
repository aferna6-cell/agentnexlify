# Run 105 — Improvement Backlog (2026-08-15-pm)

## Winner (Implemented This Run)

**route-security-guard-audit SKILL.md — Direct Implementation**
- Category: code_health
- Effort: XS (content verbatim from run 102 winning-concept.md)
- Status: IMPLEMENTED by subconscious run 105 (3rd carry-forward escalation per runs 99/101 precedents)
- File written: `.claude/skills/route-security-guard-audit/SKILL.md`
- Evidence: scoring_config.py (4 mutating routes, grep-confirmed) + appointment_briefs.py (GH #643, 8d)
- Confidence: HIGH

## Bonus Actions Executed This Run

1. **SUPABASE_ACCESS_TOKEN "Action Required" note block** — added to ops/credential-rotation-schedule.md.
   Completes run 104 winner (row pre-existed; note block was the missing piece). Step 9E noise
   continues until human fills in rotation date.

2. **GH issue for scoring_config.py block_demo_role** — filed with labels `security`, `ai-ready`.
   References GH #643 as prior instance. Lists 4 affected routes. Cites route-security-guard-audit
   SKILL.md as implementation guide.

## Active Directions (Carry-Forward)

| Direction | Source Run | Status | Notes |
|-----------|-----------|--------|-------|
| SUPABASE_ACCESS_TOKEN credential rotation | Run 104 | IMPLEMENTED (bonus action 2 this run) | Row pre-existed; note block added 2026-08-15-pm |
| Step 9C age gate: brain-connector staleness | Run 103 | IMPLEMENTED 2026-08-15 (commit 60499dd) | Fastest implementation in subconscious history |
| Step 9G: KB self-healing trigger | Run 101 | IMPLEMENTED 2026-08-06 | Fires but blocked by GH #403 (ANTHROPIC_API_KEY) |
| Step 9F: KB staleness check | Run 97/99 | IMPLEMENTED 2026-07-20 | Firing correctly per nightly log |

## Parking Lot

### Step 9E 'unknown' last_rotated handling (Idea 2 this run)
- **Problem:** Step 9E outputs "not yet set in rotation schedule" when row EXISTS with `last_rotated = "unknown"`. Parser treats missing row and unknown date identically — misleading output.
- **Fix:** Add "if unknown" branch to Step 9E bash block: output `NEEDS_DATE` instead of `not in schedule`. Log: "SUPABASE_ACCESS_TOKEN: date untracked — check ops/credential-rotation-schedule.md".
- **Risk:** Parsing-logic edit could break existing checks for AUTOPILOT_GH_TOKEN and Brain connector PAT. Additive branch is safer than it sounds but warrants testing.
- **Effort:** XS (~10 min)
- **Promote when:** Step 9E noise confirmed still firing after human checks date.

### Step 9H v2 — Idempotent PR pile-up alert (Idea 5 this run)
- **Problem:** 5 subconscious draft PRs open (#626 12d, #613 13d, #611 14d, #606 17d, #575 22d+). Human not reviewing. Original Step 9H killed run 100 (non-idempotent design would fire every nightly indefinitely).
- **Fix:** Count subconscious draft PRs; if ≥3 AND newest ≥7 days: post ONE comment on GH #394 (human attention hub) with PR titles + ages. Idempotency: check for existing comment from last 7 days before posting.
- **Effort:** S (idempotency logic is the complexity)
- **Promote when:** PR pile exceeds 6+ drafts or oldest exceeds 30 days.

### scoring_config.py block_demo_role fix (route-security-guard-audit application)
- **GH issue:** Filed this run (Bonus Action 1). Labels: security, ai-ready.
- **Routes:** POST /api/v1/scoring (seed), PUT /api/v1/scoring/{id}, DELETE /api/v1/scoring/{id}, DELETE /api/v1/scoring
- **Fix path:** Use route-security-guard-audit SKILL.md Steps 1-6.
- **Promote when:** GH #399 resolved (AUTOPILOT_GH_TOKEN rotated) — issue-to-pr-loop picks it up.

## Standing Blockers (Human-Required)

| Blocker | Age | Required Action |
|---------|-----|-----------------|
| GH #399: AUTOPILOT_GH_TOKEN expired | 37+ days | Rotate AUTOPILOT_GH_TOKEN in Railway. Unblocks 30 ai-ready issues. |
| GH #403: ANTHROPIC_API_KEY missing | 23+ days | Add ANTHROPIC_API_KEY to GH Actions Secrets. Unblocks KB autopopulate. |
| GH #394: Brain connector stalled | 23+ days | Check SUPABASE_ACCESS_TOKEN rotation. Update ops/credential-rotation-schedule.md with date. |
| GH #643: appointment_briefs.py block_demo_role | 8+ days | Merge draft PR #653 or invoke route-security-guard-audit SKILL.md. |
| scoring_config.py block_demo_role | Confirmed run 104 | Use route-security-guard-audit SKILL.md when GH #399 resolved. |

## Run 106 Candidates (Priority Order)

1. **Step 9E 'unknown' handling fix** — AUTONOMOUS-EXECUTABLE if carry-forward 1 cycle. XS effort. Eliminates misleading nightly output.
2. **Step 9H v2 idempotent PR pile alerter** — S effort. File when pile exceeds 6+ or 30+ days.
3. **Grandfathered plan gate audit** — grep `agent_os` without grandfathered checks (run 101 parking lot).
4. **Nexlify Score ai_usage_guard** — verify scoring_config.py or route-security-guard-audit SKILL.md handles this.
