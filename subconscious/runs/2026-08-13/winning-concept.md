# Run 104 — Winning Concept (2026-08-13)

## Create `.claude/skills/route-security-guard-audit/SKILL.md` [ESCALATION — DIRECT CREATION]

**Category:** code_health  
**Effort:** XS (~10 min — content pre-drafted in run 102 winning-concept.md)  
**Confidence:** HIGH  
**Status:** EXECUTED — Escalation cycle 3. Governance mandate: create directly (no human approval gate). Same precedent as Step 9F (run 99).

---

## Escalation Chain

| Run | Date | Action | Result |
|---|---|---|---|
| Run 102 | 2026-08-11-pm | RECOMMENDED | Status: pending_approval — human not yet approved |
| Run 103 | 2026-08-12-pm | CARRY-FORWARD | Status: pending_approval — still missing |
| Run 104 | 2026-08-13 | **DIRECT CREATION** | Escalation threshold met per governance.json run_104_mandate |

Precedent: Step 9F was recommended in runs 97, 98 (carry-forward), 99 (direct implementation). Step 9G followed same pattern. Escalation at cycle 3 is established governance protocol.

---

## Problem

`block_demo_role` FastAPI dependency guard prevents demo tenants from executing billing and payment operations. It must be present on every endpoint that mutates billing state, account subscriptions, or AI usage quotas.

Evidence of recurrence:
- `cbbaae5` (2026-08-07): nightly session added guard to `billing_usage.py` on detached HEAD — commits orphaned, fix never merged
- `c204af2` (2026-08-08): same fix re-applied correctly after orphaned commit discovery
- `228203d` (2026-08-08): structural test added to prevent silent regression — same day
- GH #643 (open 7 days, 2026-08-07): `appointment_briefs.py` missing `block_demo_role` + plan gate + `ai_usage_guard` — security+ai-ready labeled, autopilot loop stalled (AUTOPILOT_GH_TOKEN expired, GH #399)

Same 15-min re-discovery cost (billing.py:33 reference, test introspection pattern) paid twice in 48h. Without a skill, every new payment router will repeat this.

---

## Created SKILL.md Content

File created at: `.claude/skills/route-security-guard-audit/SKILL.md`

Six-step audit protocol:
1. Build guard inventory (`grep -rn "block_demo_role" backend/routers/`)
2. Identify missing guards (compare against billing.py:33 canonical pattern)
3. Add guard (import + `dependencies=[Depends(block_demo_role)]` + `ai_usage_guard` for AI routes)
4. Add structural test assertion (introspect `route.dependencies`, assert `block_demo_role in dep_funcs`)
5. Syntax verification (`python -c "import ast; ast.parse(...)"`)
6. Commit (two commits: fix + test, or combined)

---

## Why This Wins

1. **Escalation mandate**: governance.json run_104_mandate explicitly says "create file directly" at cycle 3.
2. **Evidence density**: 3 commits + 1 GH issue + 2 skill-discovery cycles = strongest pattern in the window.
3. **Zero implementation risk**: documentation-only change. No backend code, no auth/billing touch.
4. **Pre-drafted content**: run 102 winning-concept.md contains the full SKILL.md body. This run is copy-and-finalize.
5. **GH #643 unblocked** (partially): once AUTOPILOT_GH_TOKEN is rotated, the issue-to-pr-loop can reference this skill. Even before that, nightly sessions and human can invoke it manually.

---

## Secondary Recommendation

**pr-backlog-triage SKILL.md** (cycle 2 of escalation chain):
- Status: STILL MISSING — human has not yet approved run 103 recommendation
- Action for run 105: this is now cycle 2. If still missing, run 105 should create directly per escalation protocol.
- Evidence: 10 open PRs, 4 Dependabot aging 10+ days, morning digest flagging daily

**nightly-commit-review Detached HEAD Guard** (new recommendation):
- Add 4-line bash snippet to existing SKILL.md pre-commit section
- Evidence: cbbaae5 orphaned commits (2026-08-07), explicit skill-discovery proposal
- Effort: XS. Recommend for run 105 if this run ships cleanly.

---

## Open Blockers for Human (unchanged)

1. **#399** — Rotate AUTOPILOT_GH_TOKEN (blocking #643 and all ai-ready automation)
2. **#403** — Set ANTHROPIC_API_KEY + SUPABASE_ACCESS_TOKEN + VOYAGE_API_KEY in GitHub Secrets (embeddings skipped; FTS fallback active but degraded)
3. **#643** — appointment_briefs.py missing block_demo_role + plan gate + ai_usage_guard (7 days unaddressed)
4. **PR #653** — Merge subconscious/run-103 branch (contains run 102 + 103 + 104 artifacts including this skill file)
