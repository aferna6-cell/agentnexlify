# Improvement Backlog — 2026-06-21 (Run 65)

## Active

- **Fix GH #308 — Webhook Idempotency Early-Write Drops Payment Events** (run 65 mandate). Add `delete_key()` to `idempotency.py`; call in `stripe_webhooks.py` exception handler before re-raise. Regression test required. ~10 lines + test, human required. Sketch: `subconscious/runs/2026-06-21/winning-concept.md`.

## Parking Lot (survived debate but not chosen)

- **Fix GH #292/#293 — Wire chatbot/agent_os into plan-name dicts** (Bonus A, run 65). Active product breakage for all paid signups since repricing 2026-06-16. Full sketch: `subconscious/runs/2026-06-19-pm/winning-concept.md`. Paired with Bonus B (plan-name guard Check 7, AUTONOMOUS-EXECUTABLE after Bonus A).
- **Fix kb-autopopulate.sh — KB 46 days stale** (ROI 1.8). Root cause: agent-browser CLI not installed. Patch to use WebFetch MCP or skip CLI dependency. Compile KB to reflect 2-plan pricing, Agent OS, AI Workforce framing.
- **AI-to-Human Handoff v1** (run 4, 66 days, Critical all industries). Scope reduced to ~1 day via `os_outbound_mirror.py` (PR #188, 152 tests). Moratorium active — promote when moratorium exits. Sketch: `subconscious/runs/2026-05-28-pm/winning-concept.md`.
- **Add _TENANT_COLUMN_OVERRIDES checklist to schema-discipline.md** (3 consecutive misses: os_graph_nodes, os_graph_edges, os_action_dispatch). Low effort, prevents multi-tenant isolation gaps on future table sprints.
- **email_sequences.py god-class split** (1143L, 3 concerns: CRUD/enrollment/processor). god-class-splitter SKILL.md ready. post-split-test-repair SKILL.md ready. Unblocked since billing repricing resolved run 41 prerequisite.
- **Home.jsx god-class split** (1006L). Frontend equivalent.

## Rejected This Run

None — all ideas survived at least to parking lot.

## Questions for Next Run

1. Was GH #308 implemented? Check: `grep -n "delete_key" backend/services/idempotency.py` and `backend/routers/stripe_webhooks.py`.
2. Was GH #292/#293 (Bonus A) implemented? Check: `grep -n "chatbot" backend/services/sms_rate_limiter.py`.
3. Run 66 mandate: if GH #308 still unimplemented → winner switches to GH #292/#293.
4. Is the KB still stale? Check: `cat knowledge-base/log.md | tail -5` for last compile timestamp.
5. Has moratorium exited? Check `true_pending_estimate` — exit condition is ≤ 2 genuine pending items.
