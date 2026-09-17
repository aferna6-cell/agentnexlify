# Morning Digest — 2026-09-17

Generated: 2026-09-17 UTC | Caveman mode.

---

## Commits (last 24h)

- `37cff1f` docs(nightly): review 2026-09-17 [auto-nightly]
- `3896e31` ops: morning-digest 2026-09-16

2 commits. Nightly review ran. No feature work landed.

---

## Issues — Active / Needs Action

Non-digest open issues sorted by urgency:

| # | Title | Labels | Last Updated |
|---|-------|--------|--------------|
| #403 | Set ANTHROPIC_API_KEY in GH Actions secrets — blocks autopilot loop + KB autopopulate | critical, human-action-required | 2026-09-17 (TODAY) |
| #399 | autopilot-issue-loop GH Actions failing 5+ days — AUTOPILOT_GH_TOKEN expired | critical, human-action-required | 2026-09-11 |
| #800 | Brain connector 44+ days stale — last run 2026-07-23 | human-action-required, operational | 2026-09-17 (TODAY) |
| #827 | P1 AI cost governance: triage + meter 45 unguarded production call sites | priority/p1, billing, risk:high | 2026-09-14 |
| #767 | Website Connect v1 — one-click chatbot onboarding | priority/p0, security, customer-value | 2026-09-14 |
| #769 | M9.4 follow-up — analyze live bakeoff misses before more spend | priority/p1, diagnostic, agent-os | 2026-09-16 |
| #829 | CI: isolate recurring backend coverage failure blocking unrelated PRs | (none) | 2026-09-09 |

**78 total open issues.** 2 critical human-action-required issues still open (#403, #399).

---

## Open PRs — All Dependabot, 3 Days Old

| # | Title | Age | Notes |
|---|-------|-----|-------|
| #859 | bump vitest 4→5 in /frontend | 3d | Major version bump — review breaking changes |
| #860 | bump react 18→19 in /frontend | 3d | Major version — test widget + dashboard |
| #861 | bump react 18→19 in /demo-platform | 3d | Pair with #860 |
| #863 | bump react-dom 18→19 in /demo-platform | 3d | Pair with #861 |
| #864 | update mcp >=2.2.0,<3 in /backend | 3d | MCP protocol update — verify tool compatibility |

5 open PRs, all dependabot. No feature PRs. React 18→19 is a major version bump — needs human review before merge.

---

## Subconscious Recommendation

**Run 120 (2026-09-11-pm):** Step 9E Credential Expiry Escalation — Earlier Warning + GH Issue Filing

- AUTOPILOT_GH_TOKEN: 69 days as of Sep 11 → **~75 days today** (threshold 76d, expires ~2026-10-02, ~15 days out)
- Brain connector GitHub PAT: same age, same deadline
- Current Step 9E behavior: logs warning only. No GH issue filed. No email triggered. Zero human action in 3 consecutive nightly runs.
- Fix: edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E — add GH issue auto-filing when within 10 days of rotation threshold
- Confidence: HIGH | Effort: XS

**Token expires in ~15 days. Autonomous loop dies if not rotated.**

---

## Top 3 Priorities Today

1. **🔴 Rotate AUTOPILOT_GH_TOKEN** — expires ~2026-10-02 (~15 days). Already past 76d threshold. Powers autonomous loop, nightly review, issue-to-pr-loop. Also fix #403 (set ANTHROPIC_API_KEY in GH Actions secrets). Both are human-action-required.

2. **🟡 AI cost governance (#827)** — 45 unguarded production call sites. P1, risk:high, billing. Has been open 9 days. Cap unguarded Opus calls before cost compounds.

3. **🟡 Review React 18→19 PRs (#860, #861, #863)** — 3 coordinated dependabot PRs touching frontend + demo-platform. React 19 has breaking changes. Test widget embed + dashboard before merging.

---

## Blockers Carrying Forward

- **ANTHROPIC_API_KEY** not set in GH Actions secrets (#403) — KB autopopulate blocked since 2026-07-09.
- **Brain connector** stale 55+ days (#800) — second brain operating on stale data.
- **CI backend coverage** flaky (#829) — blocking unrelated PR merges.

---

*Next digest: 2026-09-18 ~08:00 UTC*
