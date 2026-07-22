# Run 100 — Debate Log

**Top 3 ideas debated:** Idea 1 (plan gate gap), Idea 2 (SUPABASE_ACCESS_TOKEN), Idea 4 (Step 9G Drive KB)  
**Format:** Pro / Con / Decision per idea, then head-to-head pick.

---

## Idea 1 — Fix Agent OS plan gate coverage gap

**FOR:**
- H1 severity from today's fresh audit — highest-ranking open finding
- Revenue leak is concrete: 10 routers let $19.99 tenants use $99.99 features
- Fix is precise: add `dependencies=[Depends(require_agent_os_access)]` in 10 router constructors
- Already has a test target: `backend/tests/test_plan_gating_new_plans.py` exists
- No schema change, no migration, no UI change — pure backend, low risk
- CLAUDE.md explicitly tracks plan gating: "New gates → add to `backend/tests/test_plan_gating_new_plans.py`"
- Issue will be ai-ready, executable by the issue-to-pr-loop once #399 is unblocked

**AGAINST:**
- Chatbot-plan tenants can only access these features if they've discovered the undocumented API — unlikely in practice
- Blocking legitimate future testing (os_* endpoints may be in beta preview for chatbot users)

**Assessment:** The "unlikely in practice" counter-argument doesn't hold — API keys can be shared, tenants can script against the API, and any security/billing invariant must be enforced not assumed. The "beta preview" counter is speculative with no evidence in the codebase. STRONG YES.

---

## Idea 2 — SUPABASE_ACCESS_TOKEN never set (brain connector dead)

**FOR:**
- Credential gap documented in governance `run_100_mandate` as explicit check item
- Every INGESTION-LOG.md entry since forever shows supabase connector skipped
- Brain's supabase connector would provide DB schema, live tenant patterns, migration data — high value
- Filing the issue is pure signal-surfacing with zero implementation risk

**AGAINST:**
- Not a code bug — it's a GitHub Actions secrets configuration gap (human action required)
- Already known; nightly review Step 9E already detected it; adding another GH issue duplicates signal
- Low leverage: even with token set, brain connector runs in GitHub Actions (GH_TOKEN also expired = #399)

**Assessment:** Valid parking-lot item. The double-dependency (SUPABASE_ACCESS_TOKEN + AUTOPILOT_GH_TOKEN) means filing this issue alone solves nothing until #399 is resolved. Should be a comment on #399 (bundle with token rotation) rather than a standalone issue. Demoted to bonus action.

---

## Idea 4 — Add Step 9G: Drive KB health to nightly review

**FOR:**
- Drive KB shipped last 24h (2 commits). No monitoring yet.
- Pattern already established: Step 9F (run 99) → KB autopopulate staleness. Adding Step 9G follows the same playbook.
- Would catch stale Drive sync silently, exposing tenants to outdated KB content
- Implementation purely in SKILL.md — no migration, no backend change

**AGAINST:**
- Drive KB feature is brand new. Premature to add monitoring before the feature stabilizes.
- No tenant has Drive sync active yet (feature just shipped) — monitoring would always show "no tenants syncing" for weeks
- Step 9F already sets the precedent; implementation can follow same pattern. Not urgent today.

**Assessment:** Good idea, wrong timing. Feature needs adoption before monitoring adds value. DEFER — add to parking lot for run 105 (give Drive KB 2 weeks to stabilize).

---

## Head-to-Head Pick

| | Idea 1 (plan gate) | Idea 2 (SUPABASE token) | Idea 4 (Drive KB health) |
|--|--|--|--|
| Severity | HIGH (audit H1) | MEDIUM (config gap) | LOW (premature) |
| Actionability | High — precise fix spec | Low — needs human secret | Deferred — too early |
| Revenue impact | Direct ($80/mo leak per chatbot tenant) | Indirect | None yet |
| Implementation risk | Low | None (GH issue only) | None |
| Execution path | GH issue → issue-to-pr-loop | GH issue + #399 comment | Defer |

**Winner: Idea 1.** Clear H1 severity, concrete revenue integrity impact, precise fix spec, low risk, executable by the issue-to-pr-loop.

**Bonus actions:** SUPABASE_ACCESS_TOKEN → comment on GH #399 (bundle with token rotation). GH #413 comment (REFERRAL_REWARD_ENABLED still not set, day 10+).

---

## Idea 3 kill record
**Killed after evidence check.** `zapier/authentication.js` comment at line 14 explicitly confirms 402 returned for Free/cancelled tenants. Bug #107 (2026-06-13) already fixed. Not a gap.
