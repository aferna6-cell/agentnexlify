# Nightly Commit Review — 2026-05-26

**Generated:** 2026-05-26 UTC
**Commits reviewed:** 6 (last 24h)
**Auto-fixes applied:** 1 (god-class-splitter skill creation)
**Issues opened:** 0
**Carry-forward from prior review:** GH #181 billing fix (MEDIUM)

---

## Commit Triage

| SHA | Message | Risk | Notes |
|-----|---------|------|-------|
| `96bcdb7` | subconscious: run 2026-05-25-pm (run 33) — Create god-class-splitter skill | LOW | Subconscious state files only. Winning concept proposed skill creation but SKILL.md was never written — executed as auto-fix this session. |
| `0a59147` | docs(agent-os): partner brief for Agent OS rehaul | LOW | Docs only. No production code touched. |
| `b1e0ed0` | ops: kb-drift sweep 2026-05-25 — no drift detected | LOW | Ops log. |
| `9201af9` | chore: weekly skill discovery report 2026-05-25 | LOW | Docs only. Proposed: god-class-splitter, post-split-test-repair, billing-constant-guard skills. |
| `45397c2` | ops: morning-digest 2026-05-25 | LOW | Ops log. |
| `a25f540` | ops: nightly-commit-review 2026-05-25 | LOW | Ops log. |

**Zero production code changes in the last 24h.** All commits are docs, ops logs, or subconscious planning artifacts.

---

## Auto-Fix Applied (LOW)

**Created `.claude/skills/god-class-splitter/SKILL.md`**

- Mandated by subconscious run 33 (96bcdb7) winning concept
- Execution arm for god-class splits — closes audit→fix loop that `improve-architecture` (diagnosis) and `tech-debt` (ranking) leave open
- 12-step checklist prevents the stale-importer and stale-@patch follow-up commits that appeared after both splits this week (PR #180, local_seo split)
- Also updated `.claude/skills/improve-architecture/SKILL.md` "After the Report" section to hand off CRITICAL god-class files to the new skill instead of generic `compound-engineering`
- Precedent: autonomous skill creation (7985fbb moratorium-sprint, 2ce31b2 escalation protocol)

---

## Carry-Forward: GH #181 (MEDIUM — Billing)

Open since prior review cycles. RUN 34 GOVERNANCE MANDATE per subconscious run 33.

**Fix is S-effort (~15 min):**
- Add `15000: "autopilot"` and `25000: "professional"` to `AMOUNT_TO_PLAN` in `backend/routers/billing.py:264`
- Remove `test_no_wrong_15000_mapping` + `test_no_wrong_25000_mapping` from `backend/tests/test_billing_amount_to_plan.py:38-44`
- Add `test_current_autopilot_pricing_150` and `test_current_professional_pricing_250`
- Update `test_all_four_current_tiers_present` to use `{9900, 15000, 25000, 89900}`

**NOT executed autonomously** — billing code is MEDIUM-risk, requires human approval per standing rules.

---

## Standing Items (no change)

| # | Title | Status |
|---|-------|--------|
| #181 | billing: AMOUNT_TO_PLAN missing 15000→autopilot + 25000→professional | OPEN — action required |
| #169 | Moratorium active: 5 pending items, oldest 36+ days | OPEN — day 21+ |

- Moratorium items A (check_project_invariants pre-commit) + B (widget sync guard) + D (CI eval workflow) remain highest-leverage sprint actions.
- 10 open Dependabot PRs: 8 MAJOR semver bumps (do not auto-merge), 1 PATCH (`#27 dompurify`) safe to merge, 1 MAJOR Python logger bump.

---

## Skill Discovery Follow-Up

Weekly report `9201af9` proposed 3 skills:
1. **god-class-splitter** — DONE this session
2. **post-split-test-repair** — covered as a sub-step in god-class-splitter SKILL.md; standalone skill not needed
3. **billing-constant-guard** — DEFERRED; requires billing code review (MEDIUM risk). GH #181 resolves the active instance.

---

## Invariant Checks

- No `from __future__ import annotations` introduced — PASS
- No `tenant_id` usage on leads/conversations — PASS (no production code changes)
- No `lead_stage` or `service_interest` column references — PASS
- No widget JS changes — PASS
- No secrets in new files — PASS

---

## Next Run Mandate

If GH #181 unimplemented by next morning review: governance mandate from subconscious run 33 fires (4-consecutive-run threshold). Escalate to blocking issue.
