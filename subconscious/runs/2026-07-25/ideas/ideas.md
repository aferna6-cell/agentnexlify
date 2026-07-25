# Ideas — Run 101 (2026-07-25)

## Evidence Digest

**What changed (3 days):** PR #573/#574 shipped AI booking panel (SHOW_BOOKING_PANEL marker, 85 tests, widget JS synced 3-mirror). Session batch ab1a7c2: email_sequences.py god-class split (1143→3 files), migration 187 RLS policy, booking-link fix. KB manually caught up 2026-07-23 (114→124 articles). Step 9G ABSENT — carry-forward 2.

**What's broken:** GH Actions spending limit hit 2026-07-20 (GH #500) — ALL GitHub Actions workflows dead: autopilot-issue-loop, kb-autopopulate, health checks, PR CI. 30+ ai-ready issues blocked. AUTOPILOT_GH_TOKEN expired (GH #399). ANTHROPIC_API_KEY missing from Actions (GH #403). INTEGRATIONS_ENC_KEY unprovisioned (GH #536). fastapi<0.136 cap accumulating security debt.

**What's missing:** Keys Koffee widget silent 39 days (PR #575 addresses, draft). Tenant MCP still at 1 tenant. LoopHealthPage.jsx deferred (Agent OS <5 tenants). kb_hybrid retrieval opt-in available but not enabled.

---

## Idea 1: Step 9G — KB autopopulate self-healing trigger (carry-forward)

**Evidence:** Step 9G absent from SKILL.md (grep: 0). Run 100 winner, morning-digest-2026-07-24 references it as "carry-forward 2 — Run 102 will implement directly if absent." KB currently fresh (2026-07-23, 2 days). Step 9G needed for future gaps. New wrinkle: GH Actions billing (#500) means `gh workflow run` will fail immediately — sketch needs billing-limit failure path.

**Action:** Add Step 9G bash block after Step 9F in `.claude/skills/nightly-commit-review/SKILL.md`. Update sketch: before `gh workflow run`, catch exit codes; if failure, include "Check GH Actions spending limit (#500)" as failure cause #1 alongside ANTHROPIC_API_KEY/VOYAGE_API_KEY.

**Impact:** KB freshness maintained automatically post-billing fix. Even in billing-blocked state, Step 9G will surface the exact failure reason rather than silently failing.

**Category:** operational

---

## Idea 2: Comment on GH #500 — GH Actions spending limit with comprehensive unblock checklist

**Evidence:** GH #500 OPEN "GitHub Actions down repo-wide — spending limit hit" (label: human-action-required, ops). Morning digest confirms as Top Priority #1. As of 2026-07-25 nightly: clean (2 log-only commits) — confirms Actions still blocked. GH #500 is the ROOT CAUSE blocking: GH #399 (AUTOPILOT_GH_TOKEN), GH #403 (ANTHROPIC_API_KEY), kb-autopopulate, Step 9G workflow trigger, all health-check workflows. 30 ai-ready issues stalled. Estimated 60+ engineering-hours queued behind one billing change.

**Action:** Use `mcp__github__add_issue_comment` on GH #500. Comment packages: (1) spending limit fix steps (Settings → Billing → Actions → set $5–20 cap); (2) AUTOPILOT_GH_TOKEN rotation (closes #399); (3) ANTHROPIC_API_KEY set in Actions secrets (closes #403); (4) optional: VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN for kb-autopopulate full fidelity; (5) verification step (trigger manual `kb-autopopulate.yml` run to confirm).

**Impact:** Single human action (15 min) unblocks ALL autonomous systems. Multiplier: 30 ai-ready issues, KB autopopulate, Step 9G, health check workflows. Morning digest has the steps but has NOT posted them to GH #500 as a structured comment — this adds that.

**Category:** operational

---

## Idea 3: File review-recommendation on PR #575 (tenant-silence ops alert) surfacing Keys Koffee urgency

**Evidence:** PR #575 (Fable 5): tenant_silence_alert.py + migration 188 (Managed Agents Phase 0). 38 tests pass locally. Keys Koffee widget silent 39 days. No automated alert exists without this PR. Morning digest flags as Top Priority #3. CI blind (#500) so no automated gate, but PR body has local proof. Fable 5 work confirmed clean by peer team contract review.

**Action:** Post comment on PR #575 quantifying the customer impact: "Keys Koffee silent 39 days since booking URL fix — this PR is the permanent alerting layer. Migration 188 is file-only (apply separately via Supabase MCP after merge). Local proof documented."

**Impact:** Closes Keys Koffee customer blindspot permanently. Manages Agents Phase 0 foundation.

**Category:** customer_value / operational

---

## Idea 4: fastapi cap removal — check if starlette bumped, remove fastapi<0.136 if safe

**Evidence:** GH #265 "Re-raise fastapi <0.136 cap once starlette bumped" — labeled tech-debt, OPEN. Cap was added to pin against a starlette regression. Accumulating security patch debt. Morning digest does not mention it as urgent.

**Action:** `grep "fastapi\|starlette" backend/requirements.txt` — check current pinned versions. If starlette has been bumped to >=0.136, remove fastapi cap in requirements.txt, run tests, open PR.

**Impact:** Unblocks fastapi security patches. Low risk (additive only).

**Category:** code_health

---

## Idea 5: Nightly SKILL.md Step 9G update — add GH Actions billing detection before gh workflow run

**Evidence:** Same as Idea 1, but narrower: the current Step 9G sketch (winning-concept-2026-07-23.md) doesn't mention checking billing status before triggering `gh workflow run`. When billing is exhausted, `gh workflow run` exits 0 locally but the queued run immediately fails. Without explicit billing-limit check, the failure comment on GH #403 would say "check ANTHROPIC_API_KEY" when the real problem is billing. This creates a misleading diagnostic.

**Action:** Update winning-concept.md Step 9G sketch to add: after `gh run list --limit=1 --json conclusion`, if conclusion=="failure" AND status text contains "spending limit" OR "billing", comment on GH #403 with "Step 9G: FAILED — check GitHub Actions spending limit (see #500) before checking API keys."

**Impact:** Prevents misleading diagnostics. Reduces mean-time-to-resolution when billing limit recurs.

**Category:** operational

---

## Ranking by Impact (for debate selection)

1. **Idea 2** — GH #500 comment: highest immediate multiplier (unblocks everything), autonomous-executable now
2. **Idea 1** — Step 9G carry-forward: persistent infrastructure value, carry-forward escalation applies next run
3. **Idea 3** — PR #575 review: customer retention, but morning digest already surfaces it
4. **Idea 5** — Step 9G sketch update: merged into Idea 1 (update sketch as part of carry-forward)
5. **Idea 4** — fastapi cap: lowest urgency, not load-bearing now
