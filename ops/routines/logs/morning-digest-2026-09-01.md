# Morning Digest — 2026-09-01

Generated: 2026-09-01T11:00Z

---

## Commits (last 24h) — 20 total

- `9703b24` docs(nightly): review 2026-09-01 [auto-nightly]
- `d63be4d` fix(m8): backfill CRM params when Haiku omits name/email/status (#727)
- `10c8a94` docs: auto-log bug fix from 81507fa
- `81507fa` fix(m8): complete CRM NL resolve path for create/update/stage (#726)
- `29a08b1` docs: auto-log bug fix from cb1ab75
- `cb1ab75` Merge PR #725 — fix(m8): strict agent_os_e2e split connectivity/action
- `a06b91a` fix(m8): strict agent_os_e2e — split connectivity from action execution
- `adca87d` Merge PR #724 — fix(m8): staging prep complete
- `d1a61a3` docs(m8): final live smoke recheck artifact
- `c3387ca` fix(m8): staging prep complete — agent-service deploy, e2e smoke, engine port
- `a0a92b1` docs(m8): confidence gate recheck — staging enc proof, e2e root cause
- `f60af63` docs(m8): post-PR723 rollout evidence and live smoke artifact
- `6faa099` fix(m8): staging prep complete — agent-service deploy, e2e smoke, engine port
- `ce0b4da` docs(m8): confidence gate recheck — staging enc proof, e2e root cause
- `d6d5e2d` docs(m8): post-PR723 rollout evidence and live smoke artifact
- `db4a026` Google integration hardening: Gmail send-only OAuth, E2E lead fix (#723)
- `e2d94de` feat(nightly): add Step 9K stale subconscious PR audit + fix Step 9J detection
- `6c1eecd` M8: staging credential compatibility for sb_secret_ server keys (#719)
- `1819dfc` ops: kb-drift sweep 2026-08-31 — no drift detected
- `fa83852` M8 HOLD: staging RLS on; service_role wiring scripts; step 3 gate (#716)

**Signal:** Massive M8 push — 15+ commits to CRM NL resolve path, staging prep, e2e smoke. Gmail OAuth hardened. Step 9K landed in nightly skill.

---

## Issues Opened / Updated (last 24h)

| # | Title | Status | Labels |
|---|-------|--------|--------|
| #728 | fix(agent-os): CRM field-omission guard in _extract.ts | OPEN (new today) | bug, ai-ready, agent-os |
| #684 | Brain connector 33+ days stale | OPEN | human-action-required |

### Standing critical issues (not resolved)
| # | Title | Labels | Age |
|---|-------|--------|-----|
| #687 | Voice addon double-billing gap on agent_os upgrade | billing, risk:medium | 6d |
| #669 | 95 routers missing Depends(block_demo_role) | security, critical | 12d |
| #403 | Set ANTHROPIC_API_KEY in GH Actions secrets | critical, human-action-required | 54d |

---

## Open PRs Needing Action

| # | Title | Draft | Age | Note |
|---|-------|-------|-----|------|
| #722 | bump eslint 10.7.0→10.9.1 | No | 1d | Dependabot — ready to merge |
| #721 | bump @typescript-eslint/parser 8.64.0→8.68.0 | No | 1d | Dependabot — ready to merge |
| #580 | bump actions/checkout 4→7 | No | 35d | Dependabot — stale, merge or close |
| #713 | subconscious: run 2026-09-01 (CRM guard #728 filed) | Draft | 2d | Step 9K audit PR — review |
| #693 | feat(agent-os): action layer + send_email + eval harness | Draft | 4d | Large feature — needs decision |
| #703 | feat(evals): send/L2 claim-then-execute via FakeGmailPort | Draft | 2d | Eval plumbing — paired with #693 |
| #683 | subconscious: runs #110-111 (Step 9K hook + block_demo_role) | Draft | 8d | Stale subconscious draft |
| #690 | docs(outreach): Instantly campaign email templates | Draft | 6d | Low urgency |
| #718 | ops: morning-digest 2026-08-31 | Draft | 1d | Yesterday's digest PR |
| #720 | chore: weekly skill discovery 2026-08-31 | Draft | 1d | Routine |

---

## Subconscious — Run 114 (2026-08-31-pm)

**Winner:** Step 9K — stale subconscious PR audit added to nightly skill. Already shipped (`e2d94de`). Step 9J detection also fixed (Dependabot query corrected to `author:app/dependabot`).

**Run 115 mandate:**
1. Verify Step 9K fired in today's nightly: `grep 'Step 9K' ops/routines/logs/nightly-commit-review-2026-09-01.md`
2. Count open subconscious PRs and stale (>30d) ones
3. Verify Step 9J now finds Dependabot PRs
4. Check GH #684: SUPABASE_ACCESS_TOKEN in Railway?
5. os_tool_executions.py stability — god class split candidate if stable 4d+
6. M8: OAuth/service_role HOLD resolved? Calendar+CRM deploy progress?

---

## KB Status

- Last compile: 2026-08-26 (yesterday's cron ran but no new articles in log)
- Articles: 124 in INDEX.md (last indexed 2026-07-23 batch)
- Embeddings: still deferred (no VOYAGE_API_KEY in cron env)
- No drift detected (1819dfc sweep 2026-08-31)

---

## Top 3 Priorities Today

### 1. M8 — Verify staging stability post-push
- 20 commits yesterday. PRs #723/724/725/726/727 all merged.
- Issue #728 filed (CRM field-omission guard, ai-ready) — issue-to-pr-loop should pick up.
- Action: confirm staging smoke passes. Check if service_role HOLD from #716 is cleared.

### 2. Security — Issue #669 (95 routers missing block_demo_role)
- Critical. Open 12 days. No PR yet.
- Action: assign to issue-to-pr-loop or build PR directly. This is a security regression.

### 3. Billing — Issue #687 (voice addon double-billing on agent_os upgrade)
- Risk:medium. Open 6 days. No PR yet.
- Action: create PR. Straightforward Stripe fix — should be low-effort, high-impact.

### Bonus
- Merge dependabot PRs #722 and #721 (ready, 1d old).
- Decide on #580 (actions/checkout 4→7, 35d stale).
- Human action still needed: #403 (ANTHROPIC_API_KEY in GH Actions) and #684 (SUPABASE_ACCESS_TOKEN in Railway).
