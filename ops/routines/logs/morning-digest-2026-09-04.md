# Morning Digest — 2026-09-04

Generated: 2026-09-04 (automated routine)

---

## Commits (last 24h) — 20 total

- `f72a274` docs(schema): record 195/196/197 as applied on staging and prod
- `966acb4` fix(nightly): block_demo_role on website_connect POSTs + log parse errors [auto-nightly-2026-09-04]
- `cad5137` ops: nightly-commit-review 2026-09-04
- `105a3c0` fix(m9): durable bakeoff harness + planner completeness rules
- `9589c26` Website/Chatbot Connect v1 — verify live widget before "connected" (#772)
- `ae81e5f` test(billing): Agent OS invoicing E2E proof (PR3) (#771)
- `10fcd33` feat(billing): wire Invoicing & Collections to invoice actions (#766)
- `fdcbb97` fix(m9): M9.4 bakeoff miss classification (#773)
- `bc29de4` fix(security): guard residual demo-write routes (#776)
- `ffcc70e` fix(m9): harden department scoring and Action registry manifest parity (#777)
- `f22ef04` Billing Automation v1 — typed invoice action bridge (#765)
- `27071b5` fix(m9): harden M9.4 bakeoff evaluation integrity (#764)
- `33eafe6` fix(m9): terminalize exhausted-failure workflow dependency deadlocks (#763)
- `50da659` feat(m9): M9.4 offline LLM planner bakeoff harness (#762)
- `f669390` fix(m9): harden M9.3 planner eval before LLM bakeoff (#758)
- `547de05` Merge pull request #757 from cursor/m9-3-frozen-eval
- `f8ccd20` chore(m9): strip trailing whitespace for diff hygiene
- `e2b500c` feat(m9): M9.3 frozen planner eval + deterministic validator
- `9f0dc88` Merge pull request #756 from morning-digest-2026-09-03
- `9f0dc88` Merge pull request #754 from cursor/m9-2-correction-pass

**Trend**: M9 planner bakeoff (4.x) dominating; Billing Automation v1 landed; Website/Chatbot Connect v1 merged; security hardening on demo-write routes.

---

## Issues — Open / Updated

### Critical / Blocking
- **#403** `[critical, ops]` Set ANTHROPIC_API_KEY in GH Actions secrets — blocks autopilot loop AND KB autopopulate *(open since 2026-07-09, 57 days)*
- **#684** `[human-action-required]` Brain connector 33 days stale — last run 2026-07-23 *(open since 2026-08-25)*

### P0 / P1
- **#767** `[p0, security, risk:high]` Website Connect v1 — one-click chatbot onboarding *(updated 2026-09-03)*
- **#768** `[p1, billing, risk:high]` Billing Automation v1 PR3 — Agent OS end-to-end proof *(updated 2026-09-03)*
- **#769** `[p1, diagnostic]` M9.4 follow-up — analyze live bakeoff misses before more spend *(updated 2026-09-03)*

### Maintenance / Low
- **#760** `[ai-ready, risk:low]` fix(ci): align claude-execution-layers workflow inventory count
- **#728** `[bug, ai-ready]` fix(agent-os): CRM field-omission guard in _extract.ts
- **#689** `[nightly-review, risk:low]` Silent exception blocks + misleading param name in churn_watch.py / appointment_booker.py

### Digest issues (open, stale — not actionable)
- #755, #745, #729, #717, #692, #691, #688 — prior digests, can close in batch

**Total open issues: 78**

---

## Open PRs Needing Action

| # | Title | Status | Age |
|---|-------|--------|-----|
| #788 | feat(schema): read-only schema-log vs live migration drift guard | open (not draft) | 0d |
| #780 | feat(m9): offline M9.5 shadow-path skeleton (zero I/O) | draft | 1d |
| #782 | subconscious: runs 115+116 — M9.2 dead guard fix + Step 9L unapplied migration alerter | draft | 1d |
| #779 | test(billing): dry-run staging smoke harness (stacked on #771) | draft | 1d |
| #778 | test(website-connect): migration-201 check-only staging preflight (stacked on #772) | draft | 1d |
| #761 | fix(agent-system): count Windows git-symlink skill placeholders | open (not draft) | 1d |
| #721 | chore(deps-dev): bump @typescript-eslint/parser to 8.68.0 | dependabot | 4d |
| #722 | chore(deps-dev): bump eslint to 10.9.1 | dependabot | 4d |
| #631 | chore(deps-dev): bump @vitejs/plugin-react in /demo-platform | dependabot | 32d |
| #630 | chore(deps-dev): bump vite in /demo-platform | dependabot | 32d |

**Action needed**: #788 and #761 are non-draft and ready for merge review. Dependabot #630/#631 are 32 days old — merge or close.

---

## Subconscious Recommendation (runs 113–114)

**Step 9K: Add stale subconscious draft PR audit to nightly-commit-review SKILL.md.** Warn when ≥3 open `subconscious/*` PRs are stale (>30d); escalate with PR comment at ≥5 or >60d. Mandated carry-forward from run 106. Condition confirmed: 5+ open subconscious draft PRs. Steps 9C–9J already shipped via this same channel. PR #782 represents the latest subconscious output (runs 115+116) but Step 9K itself is not yet in SKILL.md.

---

## KB Status

- Last compile: **2026-08-26** (2 runs, raw=16, wiki=4 each)
- No compile in 9 days — KB may be going stale
- **Root cause**: ANTHROPIC_API_KEY / VOYAGE_API_KEY not in GH Actions (issue #403, blocking since 2026-07-09)

---

## Top 3 Priorities for Today

1. **Review + merge #788** (schema drift guard) and **#761** (agent-system inventory count) — both are non-draft, ready to land, low risk.
2. **Close issue #403** — set `ANTHROPIC_API_KEY` in GH Actions secrets. Blocking KB autopopulate (9 days stale) and autopilot loop. One-time admin action; cannot be automated.
3. **Triage M9.4 bakeoff misses (#769)** — live planner spend is burning before this analysis is done. Do analysis before M9.5 builds further.

---

*Digest script: `ops/routines/logs/morning-digest-2026-09-04.md` | Lines: <300*
