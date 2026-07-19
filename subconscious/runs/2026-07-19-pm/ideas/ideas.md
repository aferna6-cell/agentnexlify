# Ideas — Run 99 (2026-07-19-pm)

## Evidence Summary

- Step 9F ABSENT after **3 consecutive nightly cycles** (runs 97, 98, 99)
- Root cause confirmed: nightly adds bash blocks **reactively** (when it detects health issues in commits); Step 9F is **proactive** — never triggers
- KB last ran 2026-07-13 (6 days ago) — **crosses 7-day threshold TOMORROW (2026-07-20)**
- PR #475 (23b1da5) cleared appointment_completion.py + BotHealthPage + AttributionPage from parking lot
- GH #399 OPEN Day 17+ (AUTOPILOT_GH_TOKEN expired, 30+ ai-ready issues blocked)
- GH #413 OPEN Day 28+ (REFERRAL_REWARD_ENABLED=1 not set, 7 comments on issue)
- platform_flags.py (PR #476) ships with resolve_int_setting minimum bypass — nightly flagged risk

---

## Idea 1: Step 9F — Fix the Delivery Mechanism (Direct Session Edit)

**Category:** Workflow Efficiency
**Effort:** XS (1 file edit, block already written)
**Risk:** Zero (guard wraps all failure paths)

### Problem
The nightly has failed to add Step 9F to SKILL.md for 3 consecutive cycles. Root cause is structural: nightly only adds bash blocks when it detects a health issue in recent commits. Step 9F is a proactive guard — there's no commit-based signal that would trigger it. The nightly will never add it autonomously.

Steps 9B/9C/9D/9E were all added by the nightly because they each had a reactive trigger:
- 9B: brain connector failure detected in commits
- 9C: KB article count below threshold found in commit changes
- 9D: issue-to-pr-loop stall detected
- 9E: credential rotation schedule missing from ops/

Step 9F has no reactive trigger — it's a proactive staleness check. The nightly mechanism is architecturally wrong for this task.

### Solution
Implement Step 9F directly in the next interactive session. The subconscious recommends and the human approves. The exact block is already written in `subconscious/runs/2026-07-17-pm/winning-concept.md`. 1 edit to `.claude/skills/nightly-commit-review/SKILL.md` — insert after Step 9E (line 288), before Step 10 (line 289).

### Urgency
KB crosses 7-day threshold TOMORROW. Without Step 9F, the second staleness gap would be silent.

### Why now vs run 97/98
3 cycles = pattern, not noise. The mechanism is proven broken for this task type. Carry-forward without mechanism change = 4th miss guaranteed.

---

## Idea 2: GH #413 Referral Activation — Booking Chain Now Complete

**Category:** Customer Value
**Effort:** XS (human action: set 1 Railway secret)
**Risk:** Zero (feature behind flag)

### Problem
REFERRAL_REWARD_ENABLED=1 has not been set for 28+ days. The full referral reward system is built (migration 162, all backend/frontend code live). GH #413 has 7 comments. Every day without the flag costs potential referral revenue.

### New context (PR #475)
appointment_jobs.py (auto_complete_past_appointments) shipped in PR #475. The full booking automation chain is now complete: lead capture → appointment booking → auto-completion. Referral rewards can now fire on real completed bookings, not just manual completions.

### Solution
Human sets REFERRAL_REWARD_ENABLED=1 in Railway environment. No code change. Single step.

### Why this might not win
- It's a human-action notification, not a system improvement recommendation
- 7 comments on GH #413 already — subconscious has escalated enough
- Subconscious can't set Railway secrets itself
- The right channel is PushNotification, not a winning concept
- Weakened recommendation: notify via PushNotification, don't pick as winner

---

## Idea 3: platform_flags.py Safety Registry

**Category:** Code Health / Operational
**Effort:** S (1 new file + optional guard in platform_flags.py)
**Risk:** Low

### Problem
Nightly commit review (2026-07-19) flagged: `resolve_int_setting` DB override bypasses `minimum` parameter. Setting DB value to "0" for a size/count setting (e.g. `voice_chat_max_tokens`) would pass through as-is, not floored to the minimum, causing Claude API calls to receive `max_tokens=0` and fail silently.

No production rows at risk today (all seeded as "1"), but platform_settings usage will expand as more features adopt the DB-flag pattern. The risk compounds over time.

### Solution
Create `ops/platform-flags-registry.md` documenting:
- Safe keys (feature toggles: value "0" = disabled, "1" = enabled)
- Dangerous keys (size/count settings: minimum bypass is catastrophic)
- Rule: only safe toggle keys should be set in platform_settings table

Optionally: add a SETTINGS_SAFE_KEYS allowlist to platform_flags.py that raises an error if an unsafe key is written.

### Why this might not win
- No current production risk (nightly confirmed all rows are "1")
- Medium-term operational hygiene, not urgent
- Feature flag pattern is new — registry is premature until 3+ keys exist
- Step 9F has direct urgency (KB threshold tomorrow)

---

## Idea 4: conversation_enrichment_job.py — Investigate and File Scheduling Issue

**Category:** Agent Performance / Operational
**Effort:** S (research + 1 GH issue)
**Risk:** Zero (information gathering only)

### Problem
batch_runtime.py shipped in PR #471 (2026-07-17) — reduces AI job costs 50% for offline work. conversation_enrichment_job.py is its first defined caller. But the job is NOT scheduled. Unknown:
- How many conversations are eligible for enrichment?
- What's the WHERE clause in conversation_enrichment_job.py?
- What would it cost to run batch_runtime vs standard?
- What's the correct cron cadence?

### Solution
Read `conversation_enrichment_job.py`, check conversations table for eligible record count (Supabase MCP), estimate run cost, then file a GH issue with a scheduling sketch (label: `ai-ready` once GH #399 resolves). This bypasses GH #399 because the issue can be filed directly via mcp__github__issue_write — not via issue-to-pr-loop.

### Why this might not win
- PR #471 just landed; no urgency signal
- batch_runtime.py is opt-in off by design
- Requires Supabase MCP (headless session may not have it)
- No threshold breach like KB's 7-day window
- Good future work, not today's winner

---

## Idea 5: Step 9G — GH #399 Queue Depth Alert

**Category:** Operational / Workflow Efficiency
**Effort:** S (1 SKILL.md bash block addition)
**Risk:** Zero

### Problem
GH #399 (AUTOPILOT_GH_TOKEN expired) has silently blocked 30+ ai-ready issues for 17+ days. The queue depth is invisible in daily operations. Without a signal, the token expiry continues to silently accumulate debt.

### Solution
Add Step 9G to nightly-commit-review SKILL.md: check how many ai-ready issues have no linked PR and have been open >14 days. If count > 10, add a comment to GH #399 with the queue depth. Makes the growing blocked queue visible every night.

### Why this might not win
- GH #399 itself already exists and has comments — adding more doesn't fix the token
- AUTOPILOT_GH_TOKEN requires human rotation; alert won't trigger the fix
- Step 9F must ship before Step 9G (ordering matters for SKILL.md health)
- Step 9G is downstream of the SKILL.md-edit delivery mechanism problem already present in Step 9F
- Weakened by: same delivery mechanism issue (proactive, not reactive) as Step 9F

---

## Top 3 for Debate

1. **Idea 1: Step 9F Direct Session Edit** — 3 cycles proven broken, KB threshold tomorrow, mechanism understood, block ready
2. **Idea 2: GH #413 Referral Activation** — highest ROI unlock, 28+ days pending, booking chain now complete
3. **Idea 3: platform_flags.py Safety Registry** — real operational risk, grows over time, proactive prevention

Ideas 4 and 5 are parked: Idea 4 needs Supabase MCP + has no urgency signal; Idea 5 is downstream of Idea 1's mechanism problem.
