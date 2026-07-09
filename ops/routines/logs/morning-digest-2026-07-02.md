# Morning Digest — 2026-07-02

*Auto-generated. Caveman-mode.*

---

## 🚨 ALERT: Railway API Health Probe Timed Out

**#388 [critical/uptime]** — `agentnexlify-production.up.railway.app/api/v1/healthz` request timed out at ~10:27 UTC today. `/version` endpoint returned 200, so the service may be partially alive. Needs investigation immediately.

- Filed: 2026-07-02T10:27:59Z by GitHub Actions uptime probe
- SLACK_ALERT_WEBHOOK_URL not set — no external alert fired
- Action: Check Railway dashboard, logs, container health

---

## Commits (last 24h)

- `00fc1fe` — brain: scheduled refresh from GitHub + Supabase
- `a170595` — ops: nightly-commit-review 2026-07-02
- `45e426f` — subconscious: run 2026-07-01-pm (run 76) — Zapier plan_status enforcement (de-scoped, mandate fires)

**3 commits. 0 product code. 3 ops/planning. Zero features shipped in 24h. 3+ days no production commits.**

---

## Issues Opened / Updated (24h)

| # | Title | Status | Labels |
|---|-------|--------|--------|
| **#388** | DOWNTIME: public uptime probe failing | OPEN | critical, uptime |
| #386 | Morning digest 2026-07-01 | OPEN | digest |

---

## Open PRs Needing Action

| # | Title | Age | Action |
|---|-------|-----|--------|
| **#387** | brain: sync Maps to 2026-07-01 reality + fix landing-page-v2 widget drift | 1d | Review + merge — fixes Check 13 widget drift FAIL |
| #383 | chore(deps): bump react-router-dom 7.17.0 → 7.18.0 | 3d | Safe merge (patch) |
| #382 | chore(deps-dev): bump jsdom 29.0.2 → 29.1.1 | 3d | Safe merge (patch) |
| #381 | chore(deps-dev): bump @playwright/test 1.61.0 → 1.61.1 | 3d | Safe merge (patch) |
| #380 | chore(deps-dev): bump eslint 9.39.4 → 10.6.0 | 3d | Review — major bump, may need config update |
| #372 | Referral reward: $20 credit to referrer on referee's first paid invoice | 9d | Draft — awaiting implementation |
| #86 | fix(hooks): add 4 missing post-edit checks from harness audit | 68d | Stale draft — triage or close |

---

## Subconscious Recommendation (Run 76 / 77 context)

**Run 76 winner:** Zapier `plan_status` enforcement — de-scoped to API key guard only. Mandate: implement before run 77 or escalate to CRITICAL + file GH issue directly.

**Nightly 2026-07-02 correction:** Fix is ALREADY SHIPPED. `backend/routers/zapier.py:121-128` has the guard (GH #107, closed 2026-06-13). Subconscious was tracking wrong file path (`zapier_auth.py` doesn't exist; logic is in `zapier.py`). Nightly appended correction to `subconscious/state/memory.jsonl`. **Run 77 must NOT file a GH issue for B-001 — it's done.**

**Active open loops (from nightly):**
- B-002: SMS Compliance Dashboard frontend — `pending_autonomous` (GH #385 filed, issue-to-pr-loop active)
- B-003: `email_sequences.py` god-class split — parking lot (moratorium active)
- B-004: Plan-name guard pre-commit hook — parking lot (no urgency)

---

## Standing Issues (non-digest)

| # | Title | Age | Priority |
|---|-------|-----|----------|
| **#388** | DOWNTIME: Railway API health timeout | 0d | CRITICAL |
| **#385** | Add SMS Compliance Dashboard | 1d | HIGH — pending_autonomous |
| **#373** | Duplicate migration #158 — wizard_events fix possibly unapplied to prod | 8d | MEDIUM — schema risk |
| **#378** | Widget drift: landing-page-v2 (6 consecutive failures) | 3d | MEDIUM — #387 PR fixes this |
| #68/69/70 | memory-hygiene epic issues | 9d | LOW — ai-ready |

---

## KB Health

- Last log entry: `[2026-05-05]` — 58-day autopopulate gap (network sandbox blocks outbound in this env)
- Embeddings: Supabase MCP unauthorized; FTS fallback active; Voyage embeddings deferred
- No today's updates

---

## Top 3 Priorities Today

1. **INVESTIGATE #388 DOWNTIME** — Railway API health probe timed out at 10:27 UTC. Check Railway logs, container status. `/healthz` vs `/version` discrepancy suggests partial failure (hung handler, not crash).

2. **MERGE #387** — brain Maps PR (1d old, draft). Fixes landing-page-v2 widget drift (Check 13 FAIL → PASS). Unblocks `check_project_invariants.py` going green.

3. **CLOSE B-001 IN SUBCONSCIOUS** — Zapier enforcement is live (shipped 2026-06-13). Run 77 mandate is a ghost. Verify `subconscious/state/memory.jsonl` correction stuck, confirm run 77 won't file a spurious CRITICAL issue.

---

*Next: Merge dependabot patches (#381-383), triage eslint major (#380), check if SMS Dashboard issue-to-pr-loop has activated.*
