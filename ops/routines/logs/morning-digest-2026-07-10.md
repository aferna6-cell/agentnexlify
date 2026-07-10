# Morning Digest — 2026-07-10

**Generated:** 2026-07-10 UTC  
**Routine:** morning-digest v1.0  

---

## Commits (last 24h) — 19 total

- `559903e` brain: scheduled refresh from GitHub + Supabase  
- `69b412c` subconscious: run 2026-07-10 — Step 9E credential rotation (2nd-miss escalation)  
- `b279def` ops: nightly-commit-review 2026-07-10  
- `a12a825` subconscious: run 2026-07-09-pm — Lead Source Analytics Dashboard  
- `3b30505` G3 voice scope + agent_os voice-gate fix + vertical pages + booking uptime (#405)  
- `3596009` Bookable-by-default hours seeding + weekly funnel report + IndexNow (#404)  
- `b7d97ab` dep: bump @typescript-eslint/parser 8.62→8.63 (#396)  
- `0e0ee00` Booking on by default + real SEO surface + last-call recovery email (#402)  
- `b6c1d86` docs: auto-log bug fix from dfa8201  
- `dfa8201` ops: revive dead automation + fix demo-data metric pollution (#401)  
- `6218adf` dep: bump react-router-dom 7.17→7.18 (#383)  
- `acf8bea` dep: bump jsdom 29.0.2→29.1.1 (#382)  
- `78b3c52` dep: bump @playwright/test 1.61.0→1.61.1 (#381)  
- `45be1bf` dep: bump eslint 9.39.4→10.6.0 (#380)  
- `0b5918f` dep: bump @vitest/coverage-v8 (#281)  
- `b4f657a` dep: bump vitest 4.1.8→4.1.9 (#279)  
- `8b1e44b` brain: sync Maps to 2026-07-01 + landing-page-v2 widget drift fix (#387)  
- `913f8ca` Referral reward: $20 credit gated on REFERRAL_REWARD_ENABLED=0 (#372)  
- `adbc682` ops: morning-digest 2026-07-09  

---

## Issues opened/updated (24h)

| # | Title | Status | Labels |
|---|-------|--------|--------|
| #408 | nightly [MEDIUM]: landing-page-v2/widget violates CLAUDE.md do-not-touch | OPEN | risk:medium, widget |
| #407 | nightly [HIGH]: Referral reward Stripe webhook — verify before enabling | OPEN | risk:high, billing, stripe |

---

## Open issues — human action required (BLOCKED)

| # | Title | Priority |
|---|-------|----------|
| #403 | Set ANTHROPIC_API_KEY in GitHub Actions secrets — blocks autopilot + KB autopop | **CRITICAL** |
| #399 | AUTOPILOT_GH_TOKEN expired — autopilot failing 5+ days | **CRITICAL** |
| #406 | KB auto-populate blocked: set ANTHROPIC_API_KEY as Actions secret | HIGH |
| #394 | Fix brain-refresh credentials (GitHub 403 + SUPABASE_ACCESS_TOKEN missing) | HIGH |
| #392 | Brain refresh connectors failing 4+ consecutive days | MEDIUM |
| #385 | Add SMS Compliance Dashboard (ai-ready) | MEDIUM |

**Root cause of #403/#399/#394/#406/#392:** credential expiry event 2026-07-04. AUTOPILOT_GH_TOKEN + brain PAT both expired same day. 5+ days of automation outage.

---

## Open PRs needing action

| # | Title | Draft | Age note |
|---|-------|-------|----------|
| #86 | fix(hooks): 4 missing post-edit checks from harness audit | Draft | Pending merge |
| #341 | kb: drift sweep 2026-06-22 | Draft | Stale — 18+ days |
| #328 | Billing: save-offer step before cancel (retention) | Draft | Pending |
| #327 | AI Workforce: upgrade prompt on 402 | Draft | Pending |
| #325 | Checkout fixes: kill Stripe Link emails + land paid customers on dashboard | Draft | Pending |
| #286 | feat(os+support): Agent OS fail/abstain alerts + email-routed support | Draft | Pending |
| #284 | dep: update python-jose | Open | Dependabot |
| #283 | dep: bump uvicorn | Open | Dependabot |
| #282 | dep: update stripe | Open | Dependabot |
| #280 | dep: bump react 18→19 in demo-platform | Open | Dependabot |

---

## Nightly commit review summary (2026-07-10)

- 19 commits reviewed, 2 issues opened (#407 HIGH, #408 MEDIUM)
- No LOW-risk auto-fixes applied
- #407: Referral reward webhook solid — kill-switch in place, 20 tests green. Gate: verify migration 162 applied + Stripe staging smoke before flipping REFERRAL_REWARD_ENABLED
- #408: landing-page-v2/widget touched — CLAUDE.md says do-not-touch. Decision needed: delete it or document it

---

## Subconscious recommendation

**Run 86 (2026-07-10) — Step 9E Credential Rotation Tracking:** 2nd consecutive nightly miss on this item. Embedded exact file content in winning-concept.md to eliminate ambiguity. AUTONOMOUS-EXECUTABLE. **Morning digest implementing now** (3rd-miss prevention).

**Run 85 (2026-07-09-pm) — Lead Source Analytics Dashboard:** 7 real leads captured since 2026-06-23, zero source visibility. `source` column exists but unvisualised. L effort, zero new deps. ai-ready issue to be created today.

---

## Actions taken this digest run

- [x] Created `ops/credential-rotation-schedule.md` (subconscious run 86, deliverable 1)
- [x] Added Step 9E to `.claude/skills/nightly-commit-review/SKILL.md` (run 86, deliverable 2)
- [x] Created GH issue for Lead Source Analytics with `ai-ready` label (run 85 promotion)

---

## Top 3 priorities today

1. **[HUMAN] Rotate credentials** — Fix #403 (ANTHROPIC_API_KEY → GitHub Secrets) + #399 (AUTOPILOT_GH_TOKEN → GitHub Secrets) + #394 (brain PAT + SUPABASE_ACCESS_TOKEN → Railway). Unblocks 5+ days of stalled automation. ~15 min total.

2. **[HUMAN] Referral reward gate** (#407) — Verify migration 162 applied in prod + Stripe staging smoke before flipping REFERRAL_REWARD_ENABLED=1. Already gated off, no urgency, but blocked on your review.

3. **[AUTO] Lead Source Analytics** — GH issue created with `ai-ready` label. Issue-to-pr-loop should pick up within 15 min of credential fix. One endpoint + one chart = real customer value (where are my leads coming from?).

---

## KB health

Last compile: 2026-07-09 (backfill resolved 63-day staleness). 32 articles in prod `kb_articles`. FTS active. Embeddings deferred (VOYAGE_API_KEY owner-gated). No new articles compiled last 24h — KB auto-populate blocked pending ANTHROPIC_API_KEY secret fix (#403/#406).
