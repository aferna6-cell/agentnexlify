# Run 102 — Candidate Ideas (2026-08-07)

## Evidence base
- `ops/routines/logs/nightly-commit-review-2026-08-07.md` — Step 9G fired, KB 15 days stale, GH Actions runs #269-#271 all show conclusion=success but zero KB log entries since 2026-07-23
- `knowledge-base/log.md` — last entry 2026-07-23 (15 days stale, threshold 7 days)
- `.github/workflows/kb-autopopulate.yml` — cron disabled (0 6 31 2 * = Feb 31), only workflow_dispatch
- `.claude/skills/nightly-commit-review/SKILL.md` line 318-319 — Step 9G success branch logs "SUCCESS" without verifying KB log was updated
- `docs/skill-discovery/2026-07-27.md` — feature-docs-trio pattern: 3 occurrences in 7-day window
- `docs/dev-knowledge/bug-patterns.md` 2026-08-01 entry — connector_awareness.py used `.eq("tenant_id", client_id)` on tenant_api_keys (client_id/tenant_id confusion recurring)
- `subconscious/state/memory.jsonl` run 101 parking lot: grandfathered plan gate audit, Nexlify Score token-burn guard, typed KB notes discovery banner

---

## Idea 1 — Extend Step 9G: post GH #403 comment when kb-autopopulate exits "success" but KB log is still stale
**Category:** operational
**Effort:** XS
**Evidence:** Nightly-2026-08-07 lines 58-64: "Recent runs #269-#271 (all today, 2026-08-07T05:15-06:44Z) show `conclusion: success` — but KB log shows no entries since 2026-07-23. This matches the prior silent-failure pattern (workflow exits 0 via `continue-on-error:true` despite missing ANTHROPIC_API_KEY / VOYAGE_API_KEY / SUPABASE_ACCESS_TOKEN)." Step 9G line 318-319: `if conclusion == "success": Log: "Step 9G: kb-autopopulate triggered — SUCCESS"` — no KB freshness check.
**Action:** Amend Step 9G case (a) in SKILL.md: after `conclusion == "success"`, read `knowledge-base/log.md` last entry date; calculate days since last entry; if > 1 day, post GH #403 comment "Step 9G: kb-autopopulate.yml exited 0 (success) but KB log unchanged since {last_date}. Likely cause: ANTHROPIC_API_KEY / VOYAGE_API_KEY missing or expired in GitHub Actions Secrets. Check workflow run: {url}"
**Impact:** Closes the silent-green blind spot. Next nightly detects and alerts on success-but-stale. Human gets an actionable GH #403 comment instead of silent false success.
**Not frozen:** not in frozen_ideas, not a rejected_path

---

## Idea 2 — Add kb-autopopulate.yml verification step: exit 1 if KB log not updated today
**Category:** operational
**Effort:** S
**Evidence:** Same as Idea 1. Fixing at the source (workflow) vs at the observer (SKILL.md).
**Action:** Add final step in `.github/workflows/kb-autopopulate.yml`: read `knowledge-base/log.md`, check if last entry date is today; `exit 1` if not. Changes GH Actions conclusion from "success" to "failure" on silent fails. Step 9G's existing failure handler then posts GH #403 automatically.
**Impact:** More precise fix — conclusion accurately reflects whether KB was actually updated. But requires workflow edit (higher blast radius than SKILL.md edit).
**Not frozen:** not in frozen_ideas

---

## Idea 3 — feature-docs-trio skill: trigger KB article + ADR + INDEX update when feature PR merges
**Category:** workflow_efficiency
**Effort:** S
**Evidence:** `docs/skill-discovery/2026-07-27.md`: 3 occurrences in 7-day window (commits 717c7f3/14ebe8e/d50d1e8) — all feature PRs that lacked documentation. `e0e9be6` (22-file insights feature, 1528 insertions) merged 2026-08-06 with zero KB article, zero ADR entry, zero runbook.
**Action:** Create `.claude/skills/feature-docs-trio/SKILL.md` — triggers post-feature-PR-merge: (1) KB wiki article stub in `knowledge-base/wiki/<category>/`, (2) ADR entry in `planning/decisions/`, (3) INDEX.md update. Optional runbook for complex features.
**Impact:** Systematic knowledge capture for every shipped feature. Prevents the 15+ features shipped without docs that exist in the KB gap.
**Not frozen:** not in frozen_ideas

---

## Idea 4 — Grandfathered plan gate audit: grep all feature gates for missing legacy plan names
**Category:** code_health
**Effort:** S
**Evidence:** `docs/dev-knowledge/bug-patterns.md` 2026-08-01 entry: `connector_awareness.py` used `.eq("tenant_id", client_id)` — same schema confusion class. Earlier (run 101 parking lot): commit `2869124` fixed AI Workforce gate that omitted grandfathered plans (growth, autopilot, professional, enterprise). No comprehensive audit run since then. CLAUDE.md: "Legacy/grandfathered (still honored on old contracts): growth, autopilot, professional, enterprise."
**Action:** Grep all `ALLOWED_PLANS` / plan-check logic in `backend/routers/` for presence of grandfathered plan names; file GH issue listing any gates that omit them. Read-only audit + GH issue — no code changes.
**Impact:** Prevents revenue loss from paying legacy-plan customers hitting false "not in your plan" gates. Zero implementation risk (audit only).
**Not frozen:** not in frozen_ideas

---

## Idea 5 — Typed KB notes discovery banner: one-time dismissible UI hint
**Category:** customer_value
**Effort:** M
**Evidence:** PR #632 shipped typed notes (meeting, call, proposal types) — run 101 parking lot. No UX surface added. Users have no way to discover typed notes filter capability.
**Action:** Add a one-time dismissible banner in the Notes section when typed notes exist but no filter is active. Frontend change.
**Impact:** Feature discoverability. Medium effort for UI change. Deprioritized vs operational fixes.
**Not frozen:** not in frozen_ideas
