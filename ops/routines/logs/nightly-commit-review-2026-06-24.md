# Nightly Commit Review — 2026-06-24

**Run time:** 2026-06-24 UTC  
**Commits reviewed:** 66 (last 24h)  
**Issues found:** 1 MEDIUM, 0 HIGH  
**LOW-risk auto-fixes applied:** 0  

---

## Summary

Heavy commit day — 66 commits covering referral tracking system completion, admin dashboards, vertical KB expansion, performance fixes, and dependency hardening. No critical violations found. One medium-risk issue: migration number conflict on `158_wizard_events_fix_step_range.sql`.

---

## Critical Rule Checks

| Rule | Status |
|------|--------|
| `from __future__ import annotations` in FastAPI files | CLEAN — only appears in comments/docstrings as DON'T-add reminders, not actual imports |
| `client_id` vs `tenant_id` on leads/conversations | CLEAN — new code uses `tenant_scope.py` helpers which auto-translate |
| Widget byte-identical (`widget/` vs `frontend/public/widget/`) | CLEAN — confirmed identical |
| No `lead_stage` column usage | CLEAN |
| No `service_interest` column usage | CLEAN |
| Schema changes via numbered migrations | CLEAN — all schema changes use migrations/ |

---

## MEDIUM Issues

### ISSUE-1: Duplicate migration number 158

**Commits:** `aa1f55a` (2026-06-23), `6b0a7fb` (2026-06-24)  
**Files:**
- `migrations/158_wizard_events_fix_step_range.sql` — widens wizard_events step CHECK (0–7) and adds `demo_referral` action. Added in `aa1f55a`. **NOT in schema-log. Status: likely unapplied to prod.**
- `migrations/158_allow_new_plan_names_in_tenants_check.sql` — allows `chatbot`/`agent_os` plan names in tenants_plan_check constraint. Added in `6b0a7fb`. **APPLIED to prod 2026-06-23, confirmed in schema-log.**

**Risk:** `158_wizard_events_fix_step_range.sql` appears unapplied. Step-0 wizard events (express-setup chooser) and `demo_referral` actions would be silently rejected by the DB constraint — invisible in funnel analytics. The migration file also conflicts in naming with the already-applied 158.

**Suggested fix:**
1. Rename `158_wizard_events_fix_step_range.sql` → `160_wizard_events_fix_step_range.sql` (160 is next free number after 159)
2. Apply `160_wizard_events_fix_step_range.sql` to prod via Supabase MCP
3. Update schema-log.md

**GitHub issue filed:** see #nightly-review label

---

## HIGH Issues

None.

---

## LOW Triage (no action needed)

| Commit | Description | Risk |
|--------|-------------|------|
| brain/Open Loops.md (many) | Progress tracking updates | LOW |
| `ce6510d` | KB pricing correction across 29 wiki articles | LOW |
| `01d263e` | Audit: diagnose KB embeddings break | LOW |
| `2222102` | Dev dep bump: @typescript-eslint/parser 8.58→8.62 | LOW |
| `3eaf702` | Hook: add 4 CLAUDE.md invariant checks to post-edit | LOW |
| `1f6e6e9` | Dev dep bump: vitest 4.1.8→4.1.9 | LOW |
| `5ff293e` | Dev dep bump: @playwright/test 1.60→1.61 | LOW |
| `9c37adc` | Fix copy: live-answering gate plan name (Professional→Agent OS) | LOW |
| `3ce8fad` | Schema log: apply 117+129 confirmed | LOW |
| `c8f1bde` | Fix: HTML entity em-dash check + 23 instances fixed | LOW |
| `994815b` | Docs: session summary + bug-patterns entries | LOW |
| `30b2ab8` | Brain: dependency-reduction analysis | LOW |
| `01269be` | Monitoring: replace Slack webhook with Resend email | LOW |
| `3aa0ba7` | Perf: batch scheduled-post N+1 fix in main.py | LOW |
| `e5a2b49` | Fix: campaign-send gate aligned to MARKETING_PLANS | LOW |

## MEDIUM Triage (new features/services — no bugs found)

| Commit | Description |
|--------|-------------|
| `6b1e41c/f27fb0e` | Weekly digest: surface referral stats (new service) |
| `69e6789/1cc3338` | Referral signup notification (fire-and-forget, non-blocking) |
| `3cb10d7/489eb0f` | Admin referral overview endpoint + page |
| `16bf8a7` | Referral signup attribution (best-effort, migration 159 applied) |
| `852e8b0/c625825` | Vertical expansion 10→13 (roofing, home-cleaning, veterinary) |
| `f5fb9ae/1f46788` | Vertical expansion 7→10 (law firm, restaurant, fitness) |
| `3fe118d/8523ff4` | Internal-tenant metric exclusion, FAQ seeding, ReferralCard |
| `aa1f55a/e99ad0c` | SEO 7 verticals, wizard instrumentation, churn-watch, referral stats ⚠️ contains unapplied migration 158 |
| `860dc5a/d15d3f0` | Booking nudge, tenant health dashboard, referral click tracking |
| `b8d20b5/260472f` | Lead-capture fix, funnel dashboard, referral attribution (migration 157 applied) |
| `ac76796/15402b2` | Funnel analytics, vertical presets, SEO pages, voice tests |
| `0db28ea/aba7e3c` | Lead-capture dedup fix, voice plan-gate fix |
| `e85b73f/7588161` | Harden weekly value digest targeting |
| `204ccc0` | Activate vertical-KB moat in widget chat |
| `da4d3a8` | Voyage-optional KB retrieval via Postgres FTS fallback (migration 155 applied) |
| `32ddbbf` | KB cron guard + self-hosted error_events sink (migration 156 applied) |
| `5e57bb5` | 4-lane foundation/launch pass (status page, value digest) |
| `37115e4` | KB embeddings degradation fix + untracked deps pinned |

## HIGH Triage (auth/billing — no bugs found)

| Commit | Description | Finding |
|--------|-------------|---------|
| `1cc3338` | Auth: referral signup notification hook | Fire-and-forget via safe_create_task; graceful skip on missing ref; swallowed send failures — signup never blocked. CLEAN. |
| `16bf8a7` | Auth: referral signup attribution (referred_by_widget_key) | Best-effort write to tenants, never blocks signup. Migration 159 applied. CLEAN. |
| `a62390d` | Billing: comp-activation unresolvable-plan alert level | warning→error log only. No behavior change. CLEAN. |

---

## Next recommended actions

1. **Owner action required:** Rename `158_wizard_events_fix_step_range.sql` → `160_wizard_events_fix_step_range.sql` and apply to prod. Wizard funnel step-0 entries and `demo_referral` events are silently rejected without this.
2. Vercel deploy quota was exhausted ~2026-06-23 — verify frontend deploys have resumed.
