# Subconscious Ideas — 2026-07-23 (Run 100)

## Evidence Digest

- **KB 10 days stale** (last run 2026-07-13). Step 9F CONFIRMED in SKILL.md (6 occurrences). Step 9F fired on nightly-2026-07-22: "Step 9F: KB STALE (9 days) — comment added to GH #403." KB still stale despite alert — alert fires but doesn't fix.
- **Agent OS Rounds 7-8 landed** (e646bdc + 970da66, 3 days): calls.py god-class split (1196→3 files), owner MCP server mounted at `/mcp` with per-tenant `mcp_` key auth, stage-3 plan gate on 10 OS routers, approval-loop dedupe guard, funnel metrics in admin_loop_health endpoint. First MCP tenant activation documented (281156f).
- **Nightly-2026-07-23 clean**: 7 commits reviewed, all MEDIUM or LOW, no bugs auto-fixed. Critical invariants hold across all new files.
- **Mandate items from run 99**: Step 9F PASS, Step 9F fired in nightly-2026-07-22 PASS, KB stale GH #403 comment PASS. GH #399 / GH #413 status unknown (not checked in nightly).

---

### Idea 1: Step 9G — Add kb-autopopulate self-healing trigger to nightly SKILL.md
**Evidence:** Step 9F fired on nightly-2026-07-22 (9 days stale → GH #403 comment). KB is now 10 days stale with no fix. Step 9F alerts but cannot repair. kb-autopopulate.yml (created by nightly run 82 winner) supports `workflow_dispatch`. The 63-day stale gap in 2026 was caused by empty ANTHROPIC_API_KEY/VOYAGE_API_KEY/SUPABASE_ACCESS_TOKEN secrets in the GH Actions run — same root cause may be active now. gh CLI is available in nightly for all Steps 9B-9E patterns.
**Action:** Add Step 9G bash block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9F. When staleness >7 days: (1) run `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`, (2) wait 30s, (3) check `gh run list --workflow=kb-autopopulate.yml --limit=1 --json conclusion,createdAt` for result, (4) if succeeded: log success, (5) if failed/pending: comment on GH #403 "kb-autopopulate.yml triggered but FAILED — check ANTHROPIC_API_KEY + VOYAGE_API_KEY in GH Secrets."
**Impact:** KB self-healing: no human action needed if secrets valid. Surfaces secret-rotation blocker with specific diagnostic if secrets empty. Eliminates 10+ day stale windows from the current pattern. All 3 live tenants' AI chat quality depends on KB freshness.
**Category:** operational

---

### Idea 2: LoopHealthPage.jsx — admin frontend for Agent OS loop health
**Evidence:** `admin_loop_health.py` (22710b3, PR #475) ships 5 vitals at `/api/admin/loop-health`. Round 8 (970da66) adds funnel metrics (decision-funnel counts, approval-loop dedupe state, lapsed-tenant sweep counts). Governance run 96 correction: "admin_loop_health.py (22710b3) ships /api/admin/loop-health — 5 vitals, 261 tests, no frontend." BotHealthPage.jsx implemented in PR #475 (same admin-secret pattern, same-day delivery). First MCP tenant activated — Agent OS actively used.
**Action:** Create `frontend/src/pages/LoopHealthPage.jsx` consuming `/api/admin/loop-health`. Admin-secret prompt pattern (same as BotHealthPage). Add to Sidebar.jsx, route in App.jsx. Show: approval-loop status, pending drafts count, funnel stage breakdown, decision counts by stage, last-run timestamp.
**Impact:** Reduces time-to-detect Agent OS loop regressions from hours (polling raw JSON) to seconds. Admin sees approval funnel + dedupe metrics in one page. Critical as Agent OS scales from 2-3 to 10+ tenants.
**Category:** customer_value / workflow

---

### Idea 3: calls.py split regression audit — verify all 250 voice tests green post-Round 7
**Evidence:** Round 7 (e646bdc) split calls.py (1196 lines) into calls.py (237), calls_webhooks.py (875), and voice_phone_routing.py (133) — 51-file PR with HIGH blast radius. Nightly-2026-07-23 notes "250 voice tests pass" but does not independently run them. test_voice_webhooks_split.py (17 tests) + test_suite_round7.py (15 tests) are new. Import repoints in 10+ test files (test_suite_round3.py through round7.py). Previous god-class splits (e.g., widget_helpers split) required post-split-test-repair commits.
**Action:** Run `python -m pytest backend/tests/test_voice_*.py backend/tests/test_suite_round*.py -x --tb=short -q` to independently verify. If any fail due to stale import paths, apply surgical repoints. File GH issue if systemic.
**Category:** code_health

---

### Idea 4: MCP adoption monitoring — Step 9H tracking first-activation tenant health
**Evidence:** First MCP tenant activation documented in `docs/dev-knowledge/mcp-owner-server.md` (281156f, 2026-07-23). `mcp_server.py` mounted at `/mcp`. Per-tenant `mcp_` prefix keys via `GET/POST/DELETE /api/v1/auth/mcp-key/{tenant_id}`. No monitoring exists for MCP key errors, activation rates, or auth failures. At 1 tenant, gaps are invisible; at 10 tenants, they become critical.
**Action:** Add Step 9H to nightly SKILL.md checking MCP endpoint health: `curl -s -o /dev/null -w "%{http_code}" https://$RAILWAY_BACKEND_URL/health` + check recent GH Actions for MCP-related errors. Log result. If 3+ consecutive failures: comment on a dedicated GH issue.
**Impact:** Early warning on MCP availability before it affects tenant AI workflows.
**Category:** operational

---

### Idea 5: Owner MCP server "Getting Started" guide for tenant onboarding
**Evidence:** First MCP tenant activated (281156f). `docs/dev-knowledge/mcp-owner-server.md` created in Round 7 (developer docs). No tenant-facing onboarding guide exists. `MCPSetupPage.jsx` was extended in Round 7 (77 lines). The gap between developer docs and tenant-facing onboarding is real: tenant needs to know what tools are available, what queries the MCP can answer, how to get their key.
**Action:** Write `docs/dev-knowledge/mcp-tenant-quickstart.md` covering: (1) what the owner MCP server enables, (2) how to generate a key via MCPSetupPage, (3) example Claude Desktop config JSON, (4) 5 starter prompts for each tool (leads, conversations, appointments, analytics, knowledge-base).
**Impact:** Lowers barrier for second MCP tenant. Without a quickstart, each activation requires one-on-one onboarding time.
**Category:** customer_value / workflow
