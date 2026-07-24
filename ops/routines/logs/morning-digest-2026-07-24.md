# Morning Digest — 2026-07-24

Generated: 2026-07-24 UTC | Routine: automated

---

## Commits (last 24h)

- `58b23f4` ops: nightly-commit-review 2026-07-24 [auto-nightly]
- `e9b4972` AI-triggered native booking panel via SHOW_BOOKING_PANEL marker (#573) (#574)
- `ab1a7c2` Session batch: migration 187 + brain refresh + rollout plan + governance reconciliation + email_sequences split + booking-link fix (#571)
- `b8663d8` chore: close long-running threads — ToS §4 failed-payments clause, Stripe Connect decision, brain sync [skip ci] (#569)
- `21889d7` docs(ops): refine #266 runbook with verified prod encryption state [skip ci]
- `8246ff1` docs(migrations): reconcile 185/186 to APPLIED — verified against prod [skip ci]
- `4045bec` docs: update current-tasks with subconscious run 99 status (#509)
- `2677bbf` subconscious: run 100 (2026-07-23) — Step 9G KB autopopulate self-healing trigger (#565)
- `c886b09` chore(deps): bump peter-evans/create-pull-request 6→8
- `f1c6244` chore(deps): bump actions/setup-python 5→7
- `5032680` chore(deps): bump actions/cache 4→6
- `5d9a872` chore(deps): bump actions/setup-node 4→7
- `5875043` chore(deps): bump actions/github-script 7→9
- `5d3093a` ops: morning-digest 2026-07-23

Heavy session yesterday: booking panel shipped, migration 187 (email_sequences split), brain refresh, booking-link fix. 4 Dependabot dep bumps merged. Subconscious run 100 carried Step 9G forward.

---

## Issues — open (updated recent first)

| # | Title | Status | Labels |
|---|-------|--------|--------|
| #56 | [drive-kb] Epic — Google Drive KB onboarding | OPEN | priority/p0, epic/drive-kb |
| #64 | [zapier] Epic — Zapier CRM Export | OPEN | priority/p0, epic/zapier |
| #394 | Fix brain-refresh[bot] credentials — GitHub 403 + SUPABASE_ACCESS_TOKEN missing | OPEN | human-action-required |
| **#500** | **GitHub Actions down repo-wide — spending limit hit** | **OPEN** | **human-action-required, ops** |
| **#536** | **Provision INTEGRATIONS_ENC_KEY in Railway before applying migration 176** | **OPEN** | **high-risk, infrastructure** |
| **#403** | **Set ANTHROPIC_API_KEY in GitHub Actions secrets — blocks autopilot + KB autopopulate** | **OPEN** | **critical, human-action-required** |
| **#399** | **autopilot-issue-loop dead — AUTOPILOT_GH_TOKEN expired** | **OPEN** | **human-action-required** |
| #484 | Agent OS loop health — 2026-07-20 (SUPABASE_SERVICE_KEY wrong key class) | OPEN | loop-health |
| #451 | Implement review_responder.post_response_stub — blocked on GBP OAuth creds | OPEN | — |
| #265 | Re-raise fastapi <0.136 cap once starlette bumped | OPEN | tech-debt |

**Bold = needs your hand. 4 issues blocked on secrets/credentials only you can rotate.**

---

## Open PRs

| # | Title | Age | State |
|---|-------|-----|-------|
| #577 | subconscious: run 101 — Step 9G KB self-healing trigger (carry-forward 2) | 0d | draft |
| #576 | subconscious run 101: Step 9G — KB autopopulate self-healing trigger | 1d | draft |
| #575 | Tenant-silence ops alert + Managed Agents Phase 0 prep | 1d | draft |

**PR #577 supersedes #576** — both are run 101 artifacts; close #576, review/merge #577.

**PR #575** (Fable 5): tenant silence watch + migration 188 (NOT applied — Phase 0 gate). 8 + 30 tests pass locally. First silence-watch run post-merge will fire Keys Koffee alert (expected — widget silent 39 days). Ready for review.

**CI is blind** (#500 — Actions spending limit) so all 3 PRs have no CI gate. Local proof runs documented in PR bodies.

---

## Subconscious Recommendation

**Run 101 (2026-07-24, carry-forward 2): Step 9G — KB Autopopulate Self-Healing Trigger**

Step 9F fires correctly (nightly alert on #403 when KB stale). Step 9G closes the loop: when stale >7 days, auto-trigger `kb-autopopulate.yml` + parse conclusion + comment #403 on failure with exact secrets needed. XS bash block (~30 lines), proven channel (same as Steps 9B–9F). Run 102 mandate: implement directly if still absent (3rd carry-forward). KB currently fresh (124 articles as of 2026-07-23 manual catch-up); Step 9G needed to keep it fresh automatically.

Implement: add Step 9G block after Step 9F in `.claude/skills/nightly-commit-review/SKILL.md` line ~305. Full sketch in `subconscious/runs/2026-07-24/winning-concept.md`.

---

## Knowledge Base

- Manual catch-up 2026-07-23: 8 new articles compiled across 7 categories
- INDEX.md: 114 → 124 articles (+10)
- Categories refreshed: competitors, ai_llm, frontier_ai, small_biz_saas, verticals, technical, regulations, growth
- Embeddings still skipped (VOYAGE_API_KEY absent from CI)
- FTS fallback active

---

## Top 3 Priorities Today

### 1. Fix GitHub Actions credentials (15 min total — BLOCKS EVERYTHING)
Actions down since 2026-07-20 (#500). Autopilot dead since 2026-07-04 (#399). KB autopopulate blocked (#403). 30 ai-ready issues stalled.

Steps:
- Check https://github.com/settings/billing/summary → Actions spending limit
- Rotate `AUTOPILOT_GH_TOKEN` (repo → Settings → Secrets) — needs: repo, issues write, pull-requests write, workflows write
- Set `ANTHROPIC_API_KEY` in Actions secrets (same key Railway uses)
- Optional but high-value: `SUPABASE_ACCESS_TOKEN` (service_role key) + `VOYAGE_API_KEY`
- Verify: trigger manual run of `autopilot-issue-loop.yml`

### 2. Provision INTEGRATIONS_ENC_KEY in Railway (#536) — 5 min
Migration 176 (drop plaintext OAuth tokens) committed but blocked on this key. 0 prod rows at risk. Steps in #536. After key is set: apply migration via Supabase MCP, close #536.

### 3. Review + merge PR #575 (Tenant-silence ops alert)
Fable 5 did the work. 38 tests pass locally. Close the Keys Koffee blindspot permanently. Note: first post-merge silence-watch run will fire 1 alert for Keys Koffee (correct behavior). Migration 188 is file-only — apply separately at Phase 0 start.

---

## Standing flags

- **#500 Actions billing** — repo is monitoring-blind. Scheduled ops (railway error watch, health checks, uptime watch) all failing silently.
- **Keys Koffee** (#573 partial fix) — AI booking panel shipped but widget may still be silent (39-day gap). PR #575 adds permanent alert.
- **Step 9G** — 2 carry-forward cycles. Run 102 will implement directly if absent.
- **fastapi cap** (#265) — `fastapi<0.136` still capped. Low urgency but accumulates security patch debt.
