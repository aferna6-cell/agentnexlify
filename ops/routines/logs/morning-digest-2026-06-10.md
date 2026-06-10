# Morning Digest — 2026-06-10

> Generated: 2026-06-10 UTC | Subconscious run 2026-06-10 active

---

## Commits (last 24h) — 7 total

- `5890045` subconscious: run 2026-06-10 — Fix 3 em-dash violations in Agent OS UI (unblocks Item A Check 10 wire)
- `9b9bbdb` docs: auto-log bug fix from c6805a5
- `c6805a5` fix: os_graph_nodes/edges missing from tenant_scope overrides + dispatch tests
- `1eb0a0f` subconscious: run 2026-06-09-pm — Write os_action_dispatch.py test coverage (AUTONOMOUS-EXECUTABLE)
- `c8a0460` Agent OS knowledge graph: per-tenant long-term memory (migration 133) — PR #220 merged
- `369b3c8` Agent OS Phase 4: engine-only cutover, real send, plan caps, conversational front door — PR #219 merged
- `f4f2b96` ops: morning-digest 2026-06-09

**Nightly verdict:** Run 53 (dispatch tests) implemented by c6805a5. Knowledge graph PR #220 merged. 2 major Agent OS PRs landed.

---

## Issues (opened/updated last 24h)

| # | Title | State | Labels |
|---|-------|-------|--------|
| **#213** | Emit activity_log rows for all 4 automations (dashboard parity) | OPEN | — |
| **#217** | Stripe Connect: self-serve own-payments — BLOCKED on billing-architecture | OPEN | backend |
| **#216** | Vertical agent presets + lead-qualifier control UI (the moat) | OPEN | backend, frontend |
| **#215** | Integration health dashboard + "is my widget live?" probe | OPEN | backend, frontend |
| **#214** | WordPress plugin for one-click widget install (no-code embed) | OPEN | frontend, widget |

**Carry-over open issues (critical):**
- **#206** `security` `high` — timing-safe X-Agent-Token comparison in agent-service TS (PR #209 exists, needs merge)
- **#194** `frontend` — em-dash violations blocking Item A; subconscious run 2026-06-10 fixing this tonight
- **#193** `moratorium` — 13 pending items, oldest 44+ days

---

## Open PRs Needing Action

| # | Title | Age | Draft | Action |
|---|-------|-----|-------|--------|
| **#209** | subconscious run 52 — Fix timing-safe token comparison in auth.ts | 3d | yes | **MERGE — security HIGH** |
| **#211** | Agent OS north-star: gap #1 Act hardening + gap #2 learning loop | 2d | yes | review |
| **#212** | feat(os): web-grounded research worker for Agent OS | 2d | yes | review |
| **#183** | subconscious run 33 — GH #181 billing fix (15000→autopilot, 25000→professional) | 17d | yes | **MERGE — billing bug** |
| **#200** | subconscious run 49 — Extend nightly SKILL.md scope + apply 5 JS changes | 7d | yes | review + merge (unblocks Item A+B) |
| **#190** | fix(os-workers): inject business profile into worker prompts | 13d | yes | review |
| **#182** | Split invoices.py god class into 4 service modules | 18d | yes | review |
| **#198** | chore(deps-dev): bump @typescript-eslint/parser 8.58→8.x | 8d | no | auto-merge OK |
| **#197** | chore(deps-dev): bump eslint 9.39→10.4 | 8d | no | auto-merge OK |
| **#15** | chore(deps): bump actions/upload-artifact 4→7 | 57d | no | merge or close |

---

## Subconscious Recommendation

**Run 2026-06-10:** Fix 3 em-dash violations in `MemoryPanel.jsx:180` + `AgentOS.jsx:197/224` → restores `check_project_invariants.py` exit 0 → unblocks Item A (Check 10 pre-commit wire) for tonight's nightly.

*Run 53 (2026-06-09-pm): os_action_dispatch.py test coverage — IMPLEMENTED by c6805a5.*

---

## Top 3 Priorities for Today

1. **Merge PR #209** (5 min) — timing-safe auth token fix. Security HIGH. Draft PR already exists. Just needs review + merge.

2. **Merge PR #183** (5 min) — billing bug: `AMOUNT_TO_PLAN` missing 15000→autopilot + 25000→professional. 17-day-old draft. Path confirmed: `backend/routers/billing.py:263`.

3. **Merge PR #200** (10 min) — extends nightly SKILL.md scope. Unlocks Items A+B autonomous execution (Check 10 pre-commit guard + widget sync). Dependency for tonight's nightly to execute Item A.

*Bonus: PRs #211 + #212 (Agent OS hardening + research worker) are fresh from yesterday — review when above 3 done.*

---

## KB Status

Last log entry: 2026-05-05. KB autopopulate has been blocked by network sandbox (outbound denied) and Supabase MCP auth errors since late April. 87+ articles compiled; embeddings backlog pending `VOYAGE_API_KEY` + Supabase token in cron env.
