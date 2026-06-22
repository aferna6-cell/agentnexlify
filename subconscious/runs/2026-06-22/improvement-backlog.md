# Improvement Backlog — 2026-06-22 (Run 65)

## Active

- **Add plan-name guard Check 7 to check_project_invariants.py** — validate `chatbot`+`agent_os` in `sms_rate_limiter._UNLIMITED_PLANS` + `api_key_auth._ALLOWED_PLANS`. AUTONOMOUS-EXECUTABLE. ~30 min. Nightly review authorized.

## Parking Lot (survived debate but not chosen)

- **AI-to-Human Handoff v1** (run 4, day 57+, Critical, all 7 industries) — WEAKENED this run (7th recommendation, M-effort, scheduling friction is bottleneck). os_outbound_mirror.py delivery layer ready. Product decisions needed: trigger strings, migration schema, owner notification UX. Next customer_value winner when interactive session available. Prior implementation sketch: `subconscious/runs/2026-05-28-pm/winning-concept.md`.
- **Split widget_chat.py god class** (1307L) — NEW find this run. WEAKENED: must sequence after email_sequences.py split (run 41 active_direction precedence). Promote to run 66 candidate. /god-class-splitter SKILL.md ready. Blast-radius caution: highest-traffic router file.
- **Fix kb-autopopulate.sh** (ROI 1.8, 46+ days broken, agent-browser CLI not installed) — operational fix, graceful skip or curl fallback. Restore twice-daily KB auto-population.
- **Investigate GH #263** (24 pending migrations, CRITICAL tag) — triage first: schema_migrations table vs migrations/ directory listing. Either closes phantom issue or surfaces real schema drift.
- **Split email_sequences.py** (1143L, run 41 active_direction pending_approval) — still unresolved. /god-class-splitter + /post-split-test-repair ready. Critical standing prerequisite: fix before adding AI-to-Human Handoff email sequencing.

## Rejected This Run

- None formally killed in debate. All 5 ideas survived to some status (winner, weakened, or not-debated-but-valid).

## Questions for Next Run

1. Was Check 7 implemented (grep `check_project_invariants.py` for `_check_plan_gating_constants`)? If yes: governance correction + free-choice winner from parking lot.
2. Has AI-to-Human Handoff GH issue been created or scheduled? If yes: promote to run 66 winner.
3. Has email_sequences.py split (run 41) been executed? If yes: widget_chat.py split becomes next god-class target.
4. Is GH #263 still open? If yes: triage in run 66 as S-effort investigation.
