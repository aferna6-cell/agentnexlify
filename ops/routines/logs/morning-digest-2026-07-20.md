# Morning Digest — 2026-07-20

**Generated:** 2026-07-20 UTC (automated)
**Previous digest:** GH #467 (2026-07-17)

---

## Commits (last 24h) — 1 commit

- `188ad4b` ops: nightly-commit-review 2026-07-20

**Signal:** No code shipped. Nightly review was clean — single log commit only. Codebase stable since the large 2026-07-19 session that closed #454/#465/#453 (appointment auto-complete, BotHealthPage, AttributionPage).

---

## Issues — New / Updated (last 24h)

| # | Title | State | Label | Age |
|---|-------|-------|-------|-----|
| #484 | Agent OS loop health 2026-07-20 — BLIND | OPEN | automated, loop-health | today |
| #480 | Agent OS loop health 2026-07-19 — BLIND | OPEN | automated, loop-health | 1d |
| #479 | DOWNTIME: Railway API health probe timeout | OPEN | critical, uptime | 2d |

**Loop health is BLIND for 4 consecutive days** (#470, #474, #480, #484). Root cause per issue body: `SUPABASE_SERVICE_KEY` in GitHub Actions is the anon key (RLS-filtered → returns 0 rows). Must swap to `service_role` key. Separate from the AUTOPILOT_GH_TOKEN issue.

**#479 Railway timeout** — `/healthz` timed out on 2026-07-18 probe run. `/api/v1/version` returned 200. Likely transient cold-start. No follow-up crash detected. Monitor.

---

## Persistent Human-Action-Required Blockers

| # | Title | Age | Unblocks |
|---|-------|-----|---------|
| #413 | `REFERRAL_REWARD_ENABLED=1` in Railway | **Day 28** | Referral program (100% code-complete) |
| #399 | Rotate `AUTOPILOT_GH_TOKEN` | **Day 17** | 30 ai-ready issues, autopilot loop |
| #403 / #432 | `ANTHROPIC_API_KEY` + `SUPABASE_ACCESS_TOKEN` in GH Actions | Day 16 | KB autopopulate, AttributionPage (#453) |
| #415 | Keys Koffee — add business hours | Day 26 | First tenant bookings (0 so far) |
| #484 | Swap `SUPABASE_SERVICE_KEY` → service_role in Actions | Day 4 | Loop-health visibility |
| #394 | brain-refresh[bot] GitHub 403 | Day 29 | Brain connector |

---

## Open PRs Needing Action

| # | Title | State | Age | Action |
|---|-------|-------|-----|--------|
| #483 | subconscious run 99 — Step 9F KB staleness check | DRAFT | today | **DUPLICATE — review/close** |
| #482 | subconscious run 99 — Step 9F (channel pivot) | DRAFT | 1d | **DUPLICATE — close** |
| #481 | subconscious run 99 — Step 9F (interactive session) | DRAFT | 1d | **DUPLICATE — close** |
| #478 | subconscious run 99 — Step 9F (direct implementation) | DRAFT | 2d | **DUPLICATE — close** |
| #13 | chore(deps): bump peter-evans/create-pull-request 6→8 | OPEN | 98d | low-risk — merge or close |
| #12 | chore(deps): bump actions/setup-python 5→6 | OPEN | 98d | low-risk — merge or close |
| #11 | chore(deps): bump actions/cache 4→5 | OPEN | 98d | low-risk — merge or close |

**⚠ Step 9F duplicate PRs:** Subconscious run 99 opened 4 PRs (#478, #481, #482, #483) for the same Step 9F implementation across 4 days. This is a mechanism failure — the subconscious job is not detecting the already-open PR before creating a new one. Need to: (1) pick one PR to keep or merge, (2) close the other 3, (3) add a "PR already exists?" guard to the subconscious loop.

---

## Subconscious — Runs 97/98 Winner (carry-forward)

**Step 9F: KB Autopopulate Staleness Check** — add daily KB health log to nightly-commit-review SKILL.md.
- Run 97 selected it. Run 98 confirmed SKILL.md still absent → carry-forward.
- 4 draft PRs opened, 0 merged. Mechanism broken (subconscious channel spawns PRs but doesn't merge them).
- KB last run: **2026-07-13 (7 days ago)** — at the 7-day threshold. Next stale cycle fires tomorrow.
- Step 9F was added to SKILL.md by commit `f6ea32e` (2026-07-17) but 4 follow-up PRs suggest the implementation is contested or failing verification.

---

## Context: What shipped 2026-07-18/19 (last non-trivial session)

- `6b0b0bc` — `platform_flags.py` (DB feature flags, 60s cache, fail-open), admin voice-test endpoint
- `23b1da5` — `appointment_jobs.py` (auto-complete past appointments), `AttributionPage.jsx`, `BotHealthPage.jsx`
- `6aa9ba4` — 970-file repo cleanup (verified-stale deletions)
- Migration 175 (`platform_settings`) applied to prod

All clean per nightly review. No bugs. CLAUDE.md critical invariants honored (`client_id`, no `__future__`, no `localStorage`).

---

## Top 3 Priorities Today

### 1. [HUMAN — 5 min] Fix loop-health BLIND spot — swap SUPABASE_SERVICE_KEY
4 consecutive days of zero visibility into automation loop health.
- GitHub → Repo → Settings → Secrets → Actions
- `SUPABASE_SERVICE_KEY` → replace with Supabase service_role key (not anon key)
- Verify: next loop-health GH issue should show real tenant vitals, not empty `{}`

### 2. [HUMAN — Day 17/16] Rotate AUTOPILOT_GH_TOKEN + ANTHROPIC_API_KEY (#399, #403)
Same ask as last 3 digests. Still Day 17. 30 ai-ready issues completely blocked.
- GitHub → Settings → PAT → new token (scopes: repo, issues, pull-requests, workflows)
- Repo → Settings → Secrets → `AUTOPILOT_GH_TOKEN` (new value)
- Same secrets page → `ANTHROPIC_API_KEY` (Anthropic console key)
- Unblocks: issue-to-pr-loop, KB autopopulate, AttributionPage attribution API

### 3. [HUMAN — 10 min] Clean up 4 duplicate Step 9F draft PRs (#478, #481, #482, #483)
Subconscious ran off the rails — opened 4 PRs for the same change.
- Review #483 (newest) — if the diff looks correct, merge it
- Close #478, #481, #482 with note "duplicate of #483"
- Then add guard to subconscious: check `gh pr list --head subconscious-*` before opening new PR

---

## Parking Lot (carry-forward from run 98)

| Item | Status |
|------|--------|
| `appointment_completion.py` | DONE (#454 closed, `appointment_jobs.py` shipped 2026-07-19) |
| `REFERRAL_REWARD_ENABLED=1` | Day 28 — unset |
| Keys Koffee hours (#415) | Day 26 — no action |
| `widget_chat.py` god-class split (#472) | OPEN — 1,444 lines |
| `invoices.py` god-class split (#473) | OPEN — 1,243 lines |
| GBP OAuth credentials (#451) | Blocked on tenant action |

---

_Full logs: `ops/routines/logs/`_
_Next: evening digest or next morning run_
