# Morning Digest — 2026-05-22

**Generated:** 2026-05-22 UTC
**Moratorium:** DAY 17 — 5 pending items, oldest 36 days (run 4)

---

## Commits (last 24h)

- `1f8f871` ops: nightly-commit-review 2026-05-22 — 5 commits reviewed, all LOW, zero prod changes, GH #169 escalation comment posted
- `f75d937` subconscious: run 2026-05-21-pm (run 29) — Write AI-to-Human Handoff v1 GH Issue
- `1ce1ceb` ops: morning-digest 2026-05-21

**Zero production code changes. Zero backend/frontend/widget/migration touches.**

---

## Issues (open, non-digest)

| # | Title | Status | Age |
|---|-------|--------|-----|
| #169 | [subconscious] Moratorium active: 5 pending items, oldest 30 days | OPEN | 17d |
| #114 | [ops-automation] Migration 118 — missed_call_texts, appointments schema | OPEN | 26d+ |
| #128 | [onboarding-v2] Migration 119 — extend widget_configs + vertical_presets | OPEN | 26d+ |
| #129 | [onboarding-v2] Migration 120 — encrypt integrations.access_token at rest | OPEN | 26d+ |
| #130 | [onboarding-v2] Migration 121 — welcome_email_attempts retry tracking | OPEN | 26d+ |
| #143 | [self-maintenance] Migration 122 — maintenance_suggestions + website_crawl_history | OPEN | 26d+ |

**Note:** 15+ open morning-digest issues (#155–176) are ops logs — leave open unless you want a cleanup pass.

---

## Open PRs Needing Action

| PR | Title | Age | Action |
|----|-------|-----|--------|
| #177 | feat(agent-os): chat-first Agent OS spec + P0 foundation | 1d (draft) | Review when moratorium exits |
| #85 | feat: intent engineering layer (draft) | 28d | Review post-moratorium |
| #80 | feat(onboarding-v2): Week 1 foundation (draft) | 29d | Blocked by migrations |
| #86 | fix(hooks): 4 missing post-edit checks (draft) | 27d | Small — could merge now |
| #102 | bump youtube-transcript-api requirement | 25d | **SAFE — merge now** |
| #103 | bump python-multipart 0.0.26→0.0.27 | 25d | **SAFE — merge now** |
| #104 | bump uvicorn 0.34→0.46 | 25d | **SAFE — merge now** |
| #164 | bump @playwright/test 1.59→1.60 | 11d | **SAFE — merge now** |
| #171 | bump @typescript-eslint/parser 8.58→8.59 | 4d | **SAFE — merge now** |
| #172 | bump eslint 9.39→10.4 (dev) | 4d | Safe — minor eslint major bump, verify compat |

---

## Subconscious Recommendation (runs 28 + 29)

**Run 29 winner (MEDIUM confidence):** Write AI-to-Human Handoff v1 GH Issue — 5-min docs task, moratorium-exempt, Critical gap across all 7 verticals, 36 days pending. Issue spec ready in `subconscious/runs/2026-05-21-pm/winning-concept.md`.

**Run 28 standing directive (HIGH confidence):** `/moratorium-sprint` — Items A+B+D, ~40 min, drops pending 4→2, exits moratorium. `/moratorium-sprint SKILL.md` ready at `7985fbb`.

**Key insight (run 29):** 7 consecutive sprint recommendations without invocation. Bottleneck is 40-min commitment window, not information. Run 29 offers a parallel 5-min path that bypasses the bottleneck.

---

## Moratorium Exit Map

```
Current pending:   5 (runs 4, 20, 21, 28, 29)
After run 29 done: 4 (GH issue written resolves runs 4+21)
After /moratorium-sprint (Items A+B+D): 2 → EXIT CONDITION MET (≤2)
```

**Fastest exit: write GH issue (5 min) + run /moratorium-sprint (40 min) = moratorium lifted today.**

---

## Top 3 Priorities Today

1. **Run `/moratorium-sprint`** (~40 min) — Items A (pre-commit invariant check), B (widget 3-copy sync guard), D (lead-qualifier eval CI). Drops pending 4→2 = moratorium exits after 17 days. Specs ready. One command.

2. **Write AI-to-Human Handoff v1 GH Issue** (~5 min) — Critical customer gap, all 7 verticals, 36 days stale. Moratorium-exempt. Full spec in `subconscious/runs/2026-05-21-pm/winning-concept.md`. Creates issue-to-pr-loop pickup opportunity.

3. **Merge safe dep PRs #102/#103/#104/#164/#171** (~5 min) — All flagged SAFE by subconscious. Unblock the PR board. Each is a straightforward bump with no breaking changes.

---

## Health Signals

| Signal | Status |
|--------|--------|
| Production code changes (24h) | 0 — all ops/state |
| Nightly review bugs | 0 found |
| KB last update | 2026-05-05 (17 days stale) |
| Supabase embeddings | Still failing (Unauthorized / no VOYAGE_API_KEY in cron) |
| Moratorium | DAY 17 — needs human action |
| PR backlog (safe deps) | 5 PRs mergeable now |

---

_Next: When Slack connector attached, replace GH issue step with post to #dev-standup._
