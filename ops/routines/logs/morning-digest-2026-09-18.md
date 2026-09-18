# Morning Digest — 2026-09-18

Generated: 2026-09-18T08:00Z | Routine auto-run

---

## Commits (last 24h)

- `9d2fb44` subconscious: run 2026-09-18 — Step 9E 10-day P0 credential expiry escalation
- `f46adcf` docs(nightly): review 2026-09-18 [auto-nightly]
- `5f6819f` subconscious: merge remote state into run 121
- `5deec08` subconscious: run 2026-09-17-pm — Fix Step 9G: replace gh CLI with mcp__github__actions_run_trigger
- `dafdb23` ops: morning-digest 2026-09-17

5 commits. 0 production bugs fixed. Mostly automated/subconscious loop work.

---

## Issues — Opened/Updated (last 24h)

| # | Title | Labels | Updated |
|---|-------|--------|---------|
| #403 | Set ANTHROPIC_API_KEY in GitHub Actions — blocks autopilot + KB autopopulate | critical, human-action-required, ops | today |
| #399 | autopilot-issue-loop failing 5+ days — AUTOPILOT_GH_TOKEN expired [CRITICAL] | nightly-review, human-action-required | today |
| #800 | Brain connector 44 days stale — last run 2026-07-23 | human-action-required, brain-connector | yesterday |
| #769 | M9.4 follow-up — analyze live bakeoff misses before more spend | priority/p1, diagnostic, agent-os | 2 days ago |
| #827 | P1 AI cost governance: triage and meter 45 unguarded production call sites | priority/p1, billing, risk:high | 5 days ago |
| #767 | Website Connect v1 — one-click chatbot onboarding | priority/p0, security, customer-value | 5 days ago |

Total open issues: 79

---

## Open PRs Needing Action

All 5 are Dependabot. All opened 2026-09-14 (4 days old).

| # | Title | Age | Notes |
|---|-------|-----|-------|
| #864 | mcp requirement: >=2.2.0,<3 in /backend | 4d | Moderate — mcp 2.x API may have changes |
| #863 | react-dom 18.3.1 → 19.3.0 in /demo-platform | 4d | **MAJOR bump** — needs breaking-change review |
| #861 | react 18.3.1 → 19.3.0 in /demo-platform | 4d | **MAJOR bump** — pair with #863 |
| #860 | react 18.3.1 → 19.3.0 in /frontend | 4d | **MAJOR bump** — dashboard; needs test pass |
| #859 | vitest 3→5 in /frontend (4.1.10→5.0.0) | 4d | Major — verify test suite still passes |

No PRs from human or Claude sessions. Only Dependabot queue. React 19 across frontend + demo-platform is the biggest risk item.

---

## Subconscious Recommendation

**Run 122 (today):** Step 9E P0 credential expiry tier — IMPLEMENTED after 3 carry-forwards.
- `AUTOPILOT_GH_TOKEN` last rotated 2026-07-04 → expires **2026-10-02 (14 days away)**
- Brain connector PAT: same expiry date
- Subconscious fired the autonomous-executable threshold; SKILL.md Step 9E now has 10-day P0 alert tier

**Run 121 (yesterday PM):** Step 9G — `gh` CLI replaced with `mcp__github__actions_run_trigger` for KB autopopulate.
- `gh` CLI absent in CCR sessions; Step 9G was silently failing for ~30 days
- Fix deployed; still blocked on #403 (ANTHROPIC_API_KEY missing in Actions secrets)

---

## Top 3 Priorities Today

### 1. 🔴 ROTATE CREDENTIALS — 14 days to hard stop
- `AUTOPILOT_GH_TOKEN` + Brain connector PAT expire **2026-10-02**
- When they expire: nightly review, KB autopopulate, subconscious loop commits — ALL stop
- Action: rotate both tokens in GitHub Settings → update secrets in Actions + local .env
- Tracks: #399, #403

### 2. 🟡 Close #403: Set ANTHROPIC_API_KEY in GitHub Actions
- KB autopopulate last ran 2026-08-26 — **22 days stale** (threshold 7 days)
- Step 9G fix (mcp trigger) is live but can't run without the API key
- Human-only action: add ANTHROPIC_API_KEY to repo secrets
- Tracks: #403

### 3. 🟡 Review React 19 dependabot PRs (#860, #861, #863)
- React 19 is a major bump; Concurrent Mode changes can break custom hooks + Suspense patterns
- Recommend: run `npm run build` + `npm test` locally on #860 before merging
- #861 + #863 are demo-platform; lower stakes but pair them
- Can close #859 (vitest 5) and #864 (mcp 2.x) after a quick CI check

---

## Knowledge Base Status

Last compile: 2026-08-26 (22 days stale). Blocked on #403 (ANTHROPIC_API_KEY).
FTS fallback active. Embeddings deferred (no VOYAGE_API_KEY in cron env).

---

*Next digest: 2026-09-19 08:00Z*
