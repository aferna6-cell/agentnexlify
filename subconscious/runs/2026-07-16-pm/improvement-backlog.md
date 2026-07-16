# Improvement Backlog — 2026-07-16-pm (Run 96)

## Active

- **appointment_completion.py** — auto-complete past-confirmed appointments (end_time past 30-min cutoff), fire `appointment_completed` event unlocking review requests, rebook prompts, aftercare automations. Run 95 winner confirmed absent from backend/services/ — carry-forward. AUTONOMOUS-EXECUTABLE.

## Parking Lot (survived debate, not chosen this run)

- **BotHealthPage.jsx** — frontend dashboard for admin_loop_health endpoint (/api/admin/loop-health). Endpoint ships 5 vitals (pending drafts, opportunity suggestions queue, Agent OS usage, inbound bridge status, error accumulation). Pattern: AdminFunnelPage (PR #417). L-effort. GH issue filed as Bonus B. Run 97 candidate after appointment_completion confirmed.
- **Step 9F (nightly SKILL.md)** — KB autopopulate staleness check: check knowledge-base/log.md last-entry timestamp; if >7 days stale, escalate on GH #403. AUTONOMOUS-EXECUTABLE SKILL.md edit. Run 97 candidate.

## Bonus Actions Executed This Run

- **GH #399 Day-14+ escalation** — comment posted with opportunity-cost framing (30 ai-ready issues, 60 engineering-hours blocked behind one Railway AUTOPILOT_GH_TOKEN rotation).
- **BotHealthPage.jsx GH issue** — filed with frontend/admin/medium-risk labels. No ai-ready label until GH #399 resolved.

## Rejected This Run (First Kill)

- **os_opportunities referral_activation rule** — KILLED (run 96). Mechanism mismatch: os_opportunities.py is DB-query-only; REFERRAL_REWARD_ENABLED is a Railway env-var, not a DB column. Adding env-var inspection would violate service pattern. Workaround (widget_configs column) requires schema migration. Human decision bottleneck (0 responses to 4 GH comments on #413 over 25 days) not addressable by more notification channels. Do not re-propose until: (a) REFERRAL_REWARD_ENABLED is persisted to DB/widget_configs, or (b) human activates flag directly.

## Questions for Run 97

1. Was `appointment_completion.py` committed by nightly-2026-07-17?
2. Do all 3 regression tests pass (`test_appointment_completion.py`)?
3. First real booking visible in AdminFunnelPage or Supabase? (booking URL fix 6cc3419 + auto-complete now both in place if nightly executed)
4. GH #399 resolved? (Day 15+ — single Railway AUTOPILOT_GH_TOKEN rotation)
5. GH #413 REFERRAL_REWARD_ENABLED=1 set? (Day 26+)
6. BotHealthPage.jsx GH issue filed (Bonus B)?
7. Step 9F — KB staleness check — should it win run 97?
