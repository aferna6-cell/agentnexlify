# Improvement Backlog — 2026-06-10

## Active

- Fix 3 em-dash violations in Agent OS UI copy (MemoryPanel.jsx:180, AgentOS.jsx:197/224) — AUTONOMOUS-EXECUTABLE, unblocks Item A Check 10 wire tonight

## Parking Lot (survived debate but not chosen)

- **Add tenant scope registration checklist to schema-discipline.md** — c6805a5 confirms 3rd occurrence of `_TENANT_COLUMN_OVERRIDES` miss for new tables. Append 5-question "New Table Checklist" to path-scoped rule. Promote when next Agent OS service is added. ROI ~2.0
- **Cross-tenant isolation test for os_graph_memory** — 2 tests asserting `graph_kb_entries(client_id=A)` cannot return nodes from `client_id=B`. RLS clean but no app-level safety net. Deferred until next Agent OS sprint. ROI 2.1
- **Fix kb-autopopulate.sh** (35d broken, agent-browser CLI not installed) — replace with WebFetch/curl. KB stale. ROI 1.8

## Rejected This Run

- None new — all debate ideas survived to parking lot or winner

## Questions for Next Run

1. Was the em-dash fix applied and did Item A (Check 10) wire tonight?
2. Was PR #183 merged (billing.py 15000+25000 fix)?
3. Is check-widget-sync.sh created (Item B, 46d MISSING)?
4. Are there new em-dash violations in any commits since this run?
5. Has os_graph_memory.py grown toward god-class territory (threshold 600L)?
