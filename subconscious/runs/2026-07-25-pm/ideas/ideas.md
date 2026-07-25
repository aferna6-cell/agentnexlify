# Candidate Ideas — 2026-07-25-pm (Run 102)

## Evidence Digest

- Step 9G absent from SKILL.md for 3+ cycles (runs 100, 101, two 2026-07-25 runs). 3rd carry-forward escalation rule triggered.
- GH #500: GitHub Actions spending limit hit — all CI/workflow triggers dark. `gh workflow run kb-autopopulate.yml` would fail under this condition; Step 9G must detect and report it.
- GH #399 (AUTOPILOT_GH_TOKEN expired) + GH #403 (ANTHROPIC_API_KEY missing) both open 20+ days, unfixed. Step 9G provides a concrete diagnostic path for GH #403.
- KB is currently fresh (2026-07-23, 2 days old) after a 10-day gap. Step 9G is still load-bearing for the next gap.
- Bug-patterns.md (2026-07-23): Two new entries — booking CTA rendering bug (zero bookings) fixed, and silent-green automation (Keys Koffee widget missing 5+ weeks) unfixed. PR #575 proposes tenant-silence alert.
- PR #575 (tenant-silence + Managed Agents Phase 0): draft, local proof (8+30 tests), CI dark due to GH #500.

---

### Idea 1: Step 9G — KB Autopopulate Self-Healing Trigger (3rd carry-forward: IMPLEMENT DIRECTLY)
**Evidence:** Step 9G absent from SKILL.md for 3+ consecutive runs (runs 100, 101, 2026-07-25-am, 2026-07-25-pm). Step 9F fires alert but no repair. KB was 10 days stale when selected at run 100. Carry-forward escalation rule from SKILL.md: "if rejected 3+ times, add to frozen_ideas." For implementation winners, established precedent (run 99/Step 9F): implement SKILL.md edit directly on 3rd carry-forward.
**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` to insert Step 9G bash block after Step 9F (line 305), before Step 10. Step 9G: when days_stale > 7, trigger `gh workflow run kb-autopopulate.yml`, wait 30s, check status; if failed, comment on GH #403 with specific diagnostic including GH #500 spending-limit as possible cause.
**Impact:** KB self-heals on next stale event. Failure class (expired secrets or spending limit) diagnosed to GH #403 instead of silently continuing to alert.
**Category:** operational

---

### Idea 2: Step 9H — GH Actions Spending Limit Monitor
**Evidence:** GH #500 (spending limit) is currently dark and blocking kb-autopopulate, PR CI, and autopilot-loop. No nightly monitoring detects this state. Step 9G could fail silently without this.
**Action:** Add Step 9H bash block to SKILL.md: check GH Actions billing status via `gh api /repos/aferna6-cell/agentnexlify/actions/billing/usage` or equivalent; if minutes used near/at limit, comment on GH #500 (or create new issue) with current minute count and reset date.
**Impact:** Spending limit detected proactively rather than from blind workflow failures.
**Category:** operational

---

### Idea 3: Tenant-Silence Alert via Nightly Step (PR #575 escalation path)
**Evidence:** Bug-patterns.md 2026-07-23 entry: Keys Koffee widget missing 5+ weeks, nobody noticed (silent-green automation). PR #575 proposes frontend BotHealthPage + backend endpoint but CI is dark (GH #500). A nightly SKILL.md step could monitor per-tenant outcomes (conversation count delta, widget hit rate) without CI.
**Action:** Add Step 9H or 9I nightly step: for each Agent OS tenant, check conversations table for activity in last 7 days; if zero, comment on GH #500 area or create alert issue.
**Impact:** Catches the "paying tenant gone silent" class proactively within 7 days vs 5+ weeks.
**Category:** operational / customer_value

---

### Idea 4: VOYAGE_API_KEY Credential Rotation Schedule Entry
**Evidence:** ops/credential-rotation-schedule.md created at run 87. GH #403 is ANTHROPIC_API_KEY. Nightly Step 9G diagnostic will mention VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN but neither has a rotation schedule entry. KB autopopulate uses VOYAGE_API_KEY for embeddings.
**Action:** Add VOYAGE_API_KEY to ops/credential-rotation-schedule.md with rotation cadence (90 days) and GH Actions secret name. Add reminder to check alongside ANTHROPIC_API_KEY.
**Impact:** Prevents next KB autopopulate silent failure from unknown VOYAGE_API_KEY expiry.
**Category:** operational

---

### Idea 5: Booking Panel First-Week Conversion Audit
**Evidence:** Bug-patterns.md 2026-07-23: Booking CTA was rendered as unclickable plain text for unknown duration. Fix committed but no audit of how many leads saw the broken CTA during that window. GH #88 (bookings) shows run_88_mandate referenced booking audit.
**Action:** Query conversations table for leads who received a booking URL before the fix commit date; count how many booked vs didn't. File GH issue with revenue-impact estimate.
**Impact:** Quantifies the bug's revenue cost; motivates monitoring the booking funnel going forward.
**Category:** customer_value / code_health
