# Improvement Backlog — 2026-06-07 (Run 52)

## Active
- Remove stale Item A blocker from nightly-commit-review SKILL.md:69 — 1-line deletion unlocks Check 10 autonomous wiring at tonight's 2:37 AM nightly cycle

## Critical Standing Actions (human-required, not subconscious winners due to governance)
- **Merge PR #183** — billing.py:263 still missing 15000→autopilot + 25000→professional. GH #181 day 52+. Blocks email_sequences.py split. 10 min review + merge.
- **email_sequences.py god-class split** — 1255L, 3 clean concerns. Unblocked after PR #183 merge. /god-class-splitter ready.
- **AI-to-Human Handoff v1** — Critical gap all 7 industries, day 52+. Agent OS infrastructure available.

## Parking Lot (survived debate but not chosen this run)
- **Add Item B block to nightly SKILL.md** — enables check-widget-sync.sh autonomous creation. Bonus A in winning concept. Pre-push scope ambiguity noted — include full block with explicit scope authorization.
- **Fix auth.ts timing-safe comparison (GH #206)** — `value === expected` → `crypto.timingSafeEqual`. Bonus B in winning concept. Railway private network mitigates current risk. TypeScript auth fix, ~5 min human.
- **Confirm migration 131 applied to production** — `7a621a1` created os_routing_decision + os_model_call_log tables. No production apply confirmation. Open GH issue with ops+critical labels.
- **Zapier API key plan_status enforcement** — GH #107 (52+ days). `_get_api_key_client` resolves keys without plan_status check. Route via issue-to-pr-loop ai-ready label.

## Rejected This Run
- None new. Prior rejections in governance.json rejected_paths carry forward.

## Questions for Next Run
1. Did Item A fire autonomously tonight (2:37 AM 2026-06-07)? Check git log for `ci(pre-commit): wire check_project_invariants.py as Check 10`.
2. Was PR #183 merged? Check `grep -n "15000\|25000" backend/routers/billing.py` — expect both entries present.
3. Was auth.ts timing-safe fix applied (GH #206 closed)?
4. Was migration 131 verified applied to production Supabase?
5. Did Bonus A (Item B block) get added to SKILL.md?
