# Morning Digest — 2026-07-15

Generated: 2026-07-15 UTC | Routine run

---

## Commits (last 24h)

- `922f7ac` subconscious: run 2026-07-15 — fix widget_guard._SESSION_TURN_COUNTS unbounded dict
- `9ea9b3f` ops: nightly-commit-review 2026-07-15
- `7f497bd` subconscious: run 2026-07-14-pm (run 93) — referral checklist 10/10 complete
- `a485743` Ship recommended builds: Sonnet 5, Bot-Health, photo-triage/quoting, compliance + attribution + guard + fallback (#431)
- `b08f421` docs: auto-log bug fix from 82283ea
- `82283ea` Merge PR #430: voice KB dedupe hotfix + brain frontier update (rounds 1-2)
- `4285572` brain: add frontier round 2 (vision, quoting, GEO, evals, GEPA, reactivation)
- `8f4c12e` fix(voice): remove duplicate KB-grounding block from merge collision
- `fbd8318` brain: mark 6 shipped AI moves + add 2026-07-14 frontier update
- `65f5986` Merge PR #411: pre-launch fixes + Instantly MCP + 6 product moves
- `886b8f6` fix: renumber migrations to resolve collision with main (164/165 taken)
- `66c6898` Merge remote-tracking branch 'origin/main' into claude/agent-nexlify-leverage-7fopvm
- `617c2ae` feat: legacy reminder job honors appointment_reminders_enabled toggle
- `64e16f2` feat: ship 6 product moves — proactive widget, sync lead scoring, reminders, confidence gate, KB-grounded voice, review AI
- `a1a9e1e` feat(referral+ops): grant email, demo widget seeds, error-sink digest, weekly audit (#429)
- `6635a23` brain: add AI Product Opportunities map
- `2dc472a` kb: add knowledge-base graph generator + committed graph output
- `6a502ef` kb: frontier AI refresh — model landscape H2 2026 + voice agents sub-300ms
- `811037c` KB: add frontier_ai discovery category + de-hardcode category count
- `30c8191` ops: morning-digest 2026-07-14

---

## Issues (opened/updated last 24h)

**Active (non-digest):**
- `#413` OPEN | ACTION REQUIRED: Activate referral reward — Migration 162 in prod, one env-var flip | labels: `human-action-required` `revenue` | Day 24+ stale, 4 subconscious comments unanswered
- `#432` OPEN | KB auto-populate blocked: set ANTHROPIC_API_KEY as an Actions secret | labels: `human-action-required` `ops` | Day 12+

**Bulk-closed (digest/nightly cleanup):**
- Issues #332, #337–#339, #352, #374–#376, #379, #384, #386, #389–#390, #395, #397–#398, #400, #410 — old digest issues bulk-closed 2026-07-14 ✅

---

## Open PRs (needs action)

| # | Title | State | Age |
|---|-------|-------|-----|
| #433 | Rounds 4+5: prompt caching, structured outputs, KB reranker+hybrid, Batch API | draft | 1 day |
| #86 | fix(hooks): 4 missing post-edit checks from harness audit | draft | 81 days |
| #341 | kb: drift sweep 2026-06-22 | draft | 23 days |
| #328 | Billing: save-offer step before cancel (retention, self-serve) | draft | 27 days |
| #327 | AI Workforce: upgrade prompt on 402 (not a raw error) | draft | 27 days |
| #325 | Checkout fixes: kill Stripe Link emails + land paid customers on dashboard | draft | 28 days |
| #286 | feat(os+support): Agent OS fail/abstain alerts + email-routed support form | draft | 30 days |
| #284 | chore(deps): update python-jose >=3.5.0 | open | 30 days |
| #283 | chore(deps): bump uvicorn 0.34.0→0.49.0 | open | 30 days |
| #282 | chore(deps): update stripe >=15.2.1,<16 | open | 30 days |

**Note:** #86, #341, #328, #327, #325, #286 are aging drafts. Dependabot PRs (#282, #283, #284) 30 days old with no merge.

---

## Subconscious (Run 94 — 2026-07-15)

**Winner:** Fix `backend/services/widget_guard.py:141` — replace bare `dict[str, int]` with bounded `OrderedDict` (LRU eviction, maxsize=10,000). Prevents unbounded memory growth in long-running Railway workers. 8–10 lines, no new deps, fully autonomous.

**Why now:** PR #431 shipped `widget_guard.py` yesterday. Fix while code is fresh. Memory incident at high traffic would cost 2–3h + postmortem.

**Persistent blockers (human-only, 4+ subconscious runs unresolved):**
- `REFERRAL_REWARD_ENABLED=1` in Railway Variables — 10/10 checklist items done, program ready, Day 24+ no action
- Keys Koffee GH #415 — 0 bookings, 0 business_hours rows, Day 23+, needs email/call to tenant
- GH #399 — rotate `AUTOPILOT_GH_TOKEN`, Day 12+, blocks 40 ai-ready issues
- GH #403 / #432 — add `ANTHROPIC_API_KEY` to GitHub Actions, Day 12+, blocks KB autopopulate + autopilot loop

---

## Knowledge Base

- Last log entry: 2026-07-13 — Coffee Shop/Cafe FAQ Pack compiled for live cafe tenant (G8 gap filled)
- Frontier AI articles: frontier-model-landscape-2026-h2 + ai-voice-agents-sub-300ms (2026-07-13)
- KB autopopulate: BLOCKED — `ANTHROPIC_API_KEY` missing in GH Actions secrets (GH #432, Day 12+)
- Article count: 95 wiki articles

---

## Top 3 Priorities Today

**1. Apply widget_guard.py LRU fix (autonomous)**
- File: `backend/services/widget_guard.py:141`
- Replace bare dict with `_BoundedDict(maxsize=10_000)` using `OrderedDict` + LRU eviction
- Add regression test: `backend/tests/test_widget_guard.py` — fill 10,001 sessions, assert len==10,000
- Commit: `fix(widget_guard): cap _SESSION_TURN_COUNTS at 10k entries (LRU eviction)`
- Effort: 15 min. Risk: LOW.

**2. [HUMAN] Set REFERRAL_REWARD_ENABLED=1 in Railway**
- Location: Railway Dashboard → Variables → REFERRAL_REWARD_ENABLED → set to 1 → Deploy
- Why: Referral program is 100% code-complete. This 2-min flip activates a viral acquisition channel. Day 24 of delay. 3-5x CAC reduction potential.
- Impact: First referral-converted lead claimable from existing tenant base same day.

**3. [HUMAN] Resolve GH #399 + #432 (rotate token + add API key)**
- GH #399: Rotate `AUTOPILOT_GH_TOKEN` in GitHub Settings → unblocks 40 ai-ready issues + issue-to-PR loop
- GH #432: Add `ANTHROPIC_API_KEY` to GitHub Actions secrets → unblocks KB autopopulate (72+ day data staleness)
- Both are 5-min admin tasks. Day 12+ unresolved.

---

## Parked / Next Run Mandate

- Was widget_guard LRU fix committed by nightly-2026-07-16?
- Any human response on GH #413 (REFERRAL_REWARD_ENABLED)?
- Keys Koffee GH #415 actioned?
- AttributionPage.jsx issue — file once GH #403 resolves
- BotHealthPage.jsx — no frontend for largest service in PR #431
- Aging draft PRs (#86, #341, #328) — merge or close
