# Morning Digest — 2026-09-02

Generated: 2026-09-02 UTC | Routine: `ops/routines/morning-digest`

---

## Commits (last 24h)

- `527d93c` docs(nightly): review 2026-09-02 [auto-nightly]
- `2199fb0` docs: auto-log bug fix from b57c341
- `b57c341` Merge PR #744 — sales exact email park
- `4a5669b` fix(sales): pair outer quotes; apostrophes not truncating [skip ci]
- `85b3075` fix(sales): pair quote delimiters [skip ci]
- `3023739` fix(sales): pair quote styles [skip ci]
- `5dd63cf` fix(sales): park owner exact subject/body on single-quoted send [skip ci]
- `72273a6` docs: auto-log bug fix from 7ef4d1f
- `7ef4d1f` Merge PR #743 — Gmail 401 refresh-retry + Sales exact-email fallback
- `ce08ded` fix(sales): exact-email ignores destroy words in owner body [skip ci]
- `8a60a59` fix(gmail): 401 refresh-once retry; Sales exact-email fallback [skip ci]
- `32b35b0` docs: auto-log bug fix from 188a360
- `188a360` Merge PR #742 — CI repair guardrail types
- `7c7813f` fix(ci): align execution-layer counts and Agent OS types
- `704c3c8` docs: auto-log bug fix from fd08beb
- `fd08beb` Merge PR #741 — M8 calendar marker readback fix
- `f0cbd02` fix(m8): calendar smoke matches marker in summary or description [skip ci]
- `4420bf3` Merge PR #738 — M8 ops smoke slice
- `33a9187` Merge PR #739 — Gmail persist key fix
- `7941f50` Merge PR #740 — Calendar write dedupe
- `0fbf99f` fix(m8): L2 persist and lookup use derived key only [skip ci]
- `bf328ce` fix(m8): fail-closed smoke helpers never enable send [skip ci]
- `f953655` fix(m8): derived key wins persist and lookup [skip ci]
- `973c0f8` fix(calendar): drop slot-only upsert; expose description on normalize
- `4dfba7e` fix(m8): derive and lookup same Gmail persist-key [skip ci]
- `17cb6bf` fix(m8): align live smoke with booking + safe Gmail prompt [skip ci]
- `ec68c58` ops(m8): local + GHA workaround when Cloud Agent secrets unavailable [skip ci]

**Summary:** Heavy M8 Calendar/Gmail smoke fixes + Sales quote-pairing bug cluster merged. CI guardrail count alignment.

---

## Issues Updated (open, non-digest)

**Critical / Action Required:**
- **#403** — Set `ANTHROPIC_API_KEY` in GH Actions secrets [human-action-required] — blocks autopilot + KB autopopulate. Open since 2026-07-09.
- **#669** — [security] 95 routers missing `Depends(block_demo_role)` on mutating endpoints — ai-ready, security, nightly-review. Open since 2026-08-20.
- **#684** — Brain connector 33 days stale (last run 2026-07-23) — human-action-required, brain-connector. Updated today.

**Medium:**
- **#687** — Voice addon double-billing gap: no cancellation when tenant upgrades to agent_os — billing, risk:medium. Open since 2026-08-26.
- **#728** — fix(agent-os): CRM field-omission guard in `_extract.ts` — validate name/email/status post-Haiku extraction — bug, ai-ready, agent-os. Opened 2026-09-01.

**Low:**
- **#689** — Silent exception blocks + misleading param name in `churn_watch.py` / `appointment_booker.py` — nightly-review, risk:low. Open since 2026-08-26.

---

## Open PRs Needing Action

| # | Title | Age | Status |
|---|-------|-----|--------|
| #713 | subconscious: runs 115-117 (CRM guard + Step 9L + loop stall) | 3d | Draft — active, updated today |
| #683 | subconscious: runs 110-111 (Step 9K stale PR closer) | 9d | Draft — may be superseded by #713 |
| #703 | feat(evals): send/L2 claim-then-execute via FakeGmailPort | 3d | Draft — needs review |
| #720 | chore: weekly skill discovery report 2026-08-31 | 2d | Draft |
| #722 | chore(deps-dev): bump eslint 10.7→10.9.1 | 2d | Dependabot — ready to merge |
| #721 | chore(deps-dev): bump @typescript-eslint/parser 8.64→8.68 | 2d | Dependabot — ready to merge |
| #580 | chore(deps): bump actions/checkout 4→7 | 37d | Dependabot — very stale, review |
| #730 | ops: morning-digest 2026-09-01 | 1d | Draft — stale digest PR, can close |
| #718 | ops: morning-digest 2026-08-31 | 2d | Draft — stale digest PR, can close |
| #690 | docs(outreach): record Instantly campaign email templates | 6d | Draft |

**Note:** Old digest PRs (#718, #730) accumulating. Consider closing or auto-merging digest PRs.

---

## Subconscious Recommendation

**Run 114 (2026-08-31-pm):** Step 9K implemented — nightly stale subconscious draft PR audit added to `nightly-commit-review/SKILL.md`. HIGH confidence. Carry-forward from run 113. Adds auto-escalation when ≥3 subconscious PRs stale >30d.

> Context confirms the problem is live: 5+ open `subconscious/*` PRs tracked since run 102.

---

## KB Log

Last entries: 2026-08-26 (2 discover+compile runs). Nothing today. KB cron appears healthy.

---

## Top 3 Priorities Today

1. **[Security] Fix #669** — 95 routers missing `Depends(block_demo_role)` on mutating endpoints. Pre-built GH issue, ai-ready label. This is the highest-risk open item. Pick up with issue-to-pr-loop or direct fix.

2. **[Billing] Fix #687** — Voice addon double-billing when tenant upgrades to agent_os. Medium risk, real revenue impact. Small targeted fix in Stripe webhook handler.

3. **[CRM] Fix #728** — `_extract.ts` field-omission guard (name/email/status post-Haiku). Agent OS correctness bug. ai-ready, small scope.

---

*Digest source: git log, GitHub issues/PRs, subconscious/runs/2026-08-31-pm, knowledge-base/log.md*
