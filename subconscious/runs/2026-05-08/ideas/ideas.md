# Ideation — Run 15 (2026-05-08)

**Moratorium Status:** RE-TRIGGERED. pending_approvals = 4 (runs 4, 7, 8, 14) > threshold = 3. Oldest pending = run 4 at 22 days > max_pending_age_days = 14. Both conditions met.

---

### Idea 1: Re-escalate Widget 3-Copy Sync Guard (run 7, S-effort, 14 days)
**Evidence:** Run 7 winner (2026-04-24), 14 days unimplemented. S-effort: create `scripts/check-widget-sync.sh` + wire into pre-push + fix CLAUDE.md Invariant #4 (says "2 copies", should say "3 copies"). Three confirmed widget paths: `widget/`, `frontend/public/widget/`, `landing-page-v2/widget/`. CLAUDE.md Rule #4 explicitly named as broken. No blockers. Nightly review never flagged it — genuinely below radar.
**Action:** Create `scripts/check-widget-sync.sh` that diffs all 3 widget copies and FAIL if any diverge. Wire into `scripts/hooks/pre-push`. Fix CLAUDE.md Invariant #4 to list 3 paths.
**Impact:** Prevents next widget divergence bug (broken embeds on tenant sites). Drops pending 4→3, exiting moratorium. CLAUDE.md corrected.
**Category:** code_health

---

### Idea 2: Re-escalate AI-to-Human Handoff v1 (run 4, M-effort, 22 days — moratorium protocol oldest)
**Evidence:** Oldest pending (2026-04-16 → 22 days). customer-gaps.md: Critical, all 7 industries. Infrastructure exists: conversations table, webhooks, Twilio, Resend. Explicit-trigger-only v1 scoped to 1.5-2 days. Run 4 win was the last customer-value winner; all subsequent runs (5-14) have been code_health/operational. Customer gaps have gone unaddressed for 6 weeks.
**Action:** Implement explicit-trigger handoff: add `handoff_trigger_phrases` array to widget config. When matched, route conversation to human via webhook + Resend/Twilio notification. No AI overrides after trigger.
**Impact:** Closes #1 cross-industry gap. Enables complex query handling. Competitive parity with GoHighLevel AI Employee.
**Category:** customer_value

---

### Idea 3: Re-escalate Wire check_project_invariants.py into pre-commit (run 8, S-effort, 13 days)
**Evidence:** Em-dash blocker cleared by 8f680e8 (2026-05-05). Direct run shows all 6 checks PASS. Implementation: 8-line block in `scripts/hooks/pre-commit` after Check 9. Nightly review flagged this as unblocked for 3 consecutive nights. Zero action taken. Guards against client_id/status/areas_of_interest naming violations — historically the #1 production bug class.
**Action:** Add Check 10 block to `scripts/hooks/pre-commit`. 8 lines, no deps.
**Impact:** Blocks future naming-violation bugs at commit time. Drops pending 4→3 (if paired with run 7 as bonus).
**Category:** code_health

---

### Idea 4: Wire lead qualifier golden eval to CI (run 14, S-effort, 3 days — re-escalation)
**Evidence:** Run 14 winner (2026-05-05). Harness exists at `backend/tests/evals/test_lead_qualifier_golden.py`. Issue #110 open. No `lead-qualifier-eval.yml` in `.github/workflows/` (confirmed). 17 other CI workflows present. 3 nightly reviews have flagged this. Onboarding V2 sprint active = new drift risk.
**Action:** Create `.github/workflows/lead-qualifier-eval.yml` (30 lines). Monday cron + PR trigger. Add `LEAD_QUALIFIER_AGENT_ID` GH Secret.
**Impact:** First AI regression gate. Catches silent lead classifier drift before production. Closes Issue #110.
**Category:** operational

---

### Idea 5: Fix broken KB wikilink `[[claude-cowork]]`
**Evidence:** `anthropic-finance-agents-may-2026` wiki article references `[[claude-cowork]]` — wikilink target does not exist (flagged 3 consecutive nightly reviews). KB health score 66/100 partly driven by broken wikilinks. S-effort: either create `knowledge-base/wiki/ai-llm/claude-cowork.md` stub or remove the wikilink from the article.
**Action:** Create a stub article for Claude's collaborative features at `knowledge-base/wiki/ai-llm/claude-cowork.md` or remove the broken wikilink. Run `kb-health.py --check` to verify score improvement.
**Impact:** Removes recurring nightly review noise. Improves KB health score. 15-minute fix.
**Category:** operational
