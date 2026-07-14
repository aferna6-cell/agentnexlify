# Morning Digest — 2026-07-14

Generated: 2026-07-14 UTC | Caveman mode

---

## Commits (last 24h)

- `5043a59` brain: scheduled refresh from GitHub + Supabase
- `f79b43a` subconscious: run 2026-07-13-pm (run 92) — Day-21 Keys Koffee booking escalation
- `e4fc30f` docs: auto-log bug fix from 7a9047f
- `7a9047f` fix(os): connect prompt fired for no one — dashboard threads with source='chat' (#427)
- `97c2649` docs(planning): mark #422 fixed in Keys Koffee packet risk notes (#426)
- `c9e9071` docs: auto-log bug fix from f19c21c
- `f19c21c` fix(widget): tolerate double-encoded business hours (GH #422) (#425)
- `45401ec` feat(os): agent prompts to connect missing integrations in chat (#424)
- `47cec43` docs(ops): Keys Koffee voice packet + INTEGRATIONS_ENC_KEY runbook (#423)
- `6f3e11f` chore(deps-dev): bump vitest 4.1.9→4.1.10 in /demo-platform (#421)
- `b083a20` chore(deps-dev): bump @vitejs/plugin-react in /demo-platform (#420)
- `bbb3472` chore(deps): bump recharts 3.7.0→3.9.2 in /frontend (#419)
- `b8129d7` chore(deps-dev): bump vite 8.0.16→8.1.4 in /frontend (#418)

> 13 commits. Active day. Two bug fixes shipped + OS integration prompting feature.

---

## Open Issues (recent activity)

| # | Title | Status |
|---|-------|--------|
| #413 | ACTION REQUIRED: Activate referral reward — one env-var flip | OPEN — blocked on human |
| #415 | ACTION REQUIRED: Keys Koffee — add business hours to enable bookings (Day 21) | OPEN — **critical** |
| #412 | ACTION REQUIRED: Booking funnel diagnostic — 0 real bookings 18+ days post-launch | OPEN — diagnostic confirmed |
| #407 | nightly-review [HIGH]: Referral reward Stripe webhook — verify before enabling | OPEN — blocking #413 |
| #399 | autopilot-issue-loop GH Actions failing 5+ days — AUTOPILOT_GH_TOKEN expired | OPEN — infra blocker |
| #403 | Set ANTHROPIC_API_KEY in GH Actions secrets — blocks autopilot loop + KB auto-pop | OPEN — infra blocker |
| #406 | KB auto-populate blocked: ANTHROPIC_API_KEY not set as Actions secret | OPEN — infra blocker |
| #392 | Brain refresh connectors failing 4+ days (GitHub 403, Supabase missing token) | OPEN — infra blocker |
| #394 | Fix brain-refresh[bot] credentials — GitHub 403 + SUPABASE_ACCESS_TOKEN missing | OPEN — infra blocker |
| #266 | security: finish integrations-secret encryption — backfill + sunset plaintext | OPEN — ongoing |

---

## Open PRs Needing Action

| # | Title | Age | Draft |
|---|-------|-----|-------|
| #411 | Pre-launch audit + Instantly MCP + P0 blocker fixes | 4 days | Yes |
| #328 | Billing: save-offer step before cancel (retention, self-serve) | 26 days | Yes |
| #327 | AI Workforce: upgrade prompt on 402 (not a raw error) | 26 days | Yes |
| #325 | Checkout fixes: kill Stripe Link emails + land paid customers on dashboard | 27 days | Yes |
| #286 | feat(os+support): Agent OS fail/abstain alerts + email-routed support form | 29 days | Yes |
| #284 | chore(deps): update python-jose ≥3.3.0→≥3.5.0 in /backend | 29 days | No — ready |
| #283 | chore(deps): bump uvicorn 0.34.0→0.49.0 in /backend | 29 days | No — ready |
| #282 | chore(deps): update stripe ≥11→≥15 in /backend | 29 days | No — ready |
| #86 | fix(hooks): add 4 missing post-edit checks from harness audit | 80 days | Yes — stale |
| #341 | kb: drift sweep 2026-06-22 | 22 days | Yes — stale |

> deps PRs #282, #283, #284 are non-draft and appear merge-ready. #411 is the main active PR.

---

## Subconscious Recommendation

**Run 92 (2026-07-13-pm) winner:** Post Day-21 escalation comment on GH #415 (Keys Koffee) — diagnostic confirmed (booking_enabled=true, 0 business_hours rows), code fix merged (#422), first real booking reachable today if hours are configured.

**Run 91 (2026-07-13-am) winner:** Post code-evidence answers to 3 of 5 open checklist items in GH #413 (referral activation) — reduces human checklist burden by 60% before flipping REFERRAL_REWARD_ENABLED=1.

> Both already acted on by subconscious. Human follow-through needed on Keys Koffee contact.

---

## KB Status

- Last compile: 2026-07-13 14:35 UTC — Coffee Shop/Cafe FAQ Pack (G8 vertical, cafe tenant)
- No new compile since then. Next cron: 18:00 UTC today.
- 4 pending articles need Voyage embedding backfill (VOYAGE_API_KEY owner-gated).

---

## Top 3 Priorities Today

1. **Contact Keys Koffee — get business hours configured** (#415, #412)
   Zero real bookings at Day 21. Code is fixed (#422 merged). One email/call unlocks first booking.
   Exact action: email Keys Koffee, collect hours, enter in dashboard Settings → Business Hours.

2. **Set GitHub Actions secrets to unblock infra** (#399, #403, #406, #392, #394)
   Five open issues trace to same root: ANTHROPIC_API_KEY + AUTOPILOT_GH_TOKEN expired/missing in GH Actions.
   Fix once → autopilot loop, KB auto-populate, and brain-refresh all resume.
   Secrets to set: `ANTHROPIC_API_KEY`, `AUTOPILOT_GH_TOKEN`, `SUPABASE_ACCESS_TOKEN`.

3. **Merge deps PRs #282, #283, #284 + review #411** 
   Dep bumps are non-draft and 29 days old. Stripe, uvicorn, python-jose — all security-relevant.
   #411 (pre-launch audit) needs a human review pass before merge.

---

*Next digest: 2026-07-15 morning | Subconscious runs 93+ will fire tonight*
