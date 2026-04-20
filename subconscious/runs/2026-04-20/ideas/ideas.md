# Candidate Ideas — 2026-04-20

Evidence base: git log 3 days (Apr 17-20), audit-architecture-2026-04-18.md, bug-patterns.md (7 entries),
customer-gaps.md, current-tasks.md, knowledge-base/INDEX.md, governance.json + memory.jsonl (4 prior runs).

---

### Idea 1: Migration Duplicate Number Pre-commit Guard
**Evidence:** `audits/audit-architecture-2026-04-18.md` HIGH finding — `migrations/005_appointments.sql` vs
`005_automation_sequences.sql`; `007_google_calendar_integration.sql` vs `007_team_members.sql` vs
`007_webhooks.sql`. Audit explicitly proposes: "Enforce strict sequential check in
`scripts/hooks/pre-commit` for numbers ≥106." CLAUDE.md Rule 8: "Schema changes only via numbered
migration files." Run 3's JS silent-catch guard established the pattern of extending pre-commit — this
is the same mechanic applied to migration filenames.
**Action:** Add Check 8 to `scripts/hooks/pre-commit`: grep staged files for `migrations/` pattern,
extract leading number, detect any number ≤105 (already locked historical), and for ≥106 detect
duplicate numbers vs existing files. Emit FAIL on duplicate. Reinstall via `bash scripts/install-hooks.sh`.
**Impact:** Permanently prevents future migration replay bugs. S-effort (bash filename grep). Zero
infrastructure uncertainty. Compounds on every future migration.
**Category:** code_health

---

### Idea 2: widget_helpers.py Phase 1 — Extract Lead Capture into widget_lead_helpers.py
**Evidence:** `audits/audit-architecture-2026-04-18.md` HIGH — `widget_helpers.py` at 1,635 lines;
3rd consecutive audit HIGH (carried from 2026-04-16). Governance parking-lot entry: "Widget Hot-Zone
Regression Suite — widget_helpers.py changed 8×/7 days, 3 bugs there." `bug-patterns.md` Apr 15:
two widget-adjacent lead-capture bugs (ExtractorError, session_id dedup). CLAUDE.md Rule 9: factor god
classes before adding more. Audit proposed exact split: `widget_chat_helpers.py` + `widget_lead_helpers.py`
+ `widget_booking_helpers.py`.
**Action:** Extract `_enrich_lead_from_message`, `_capture_leads_from_session`, and related helpers
(~300L) into `backend/routers/widget_lead_helpers.py`. Update 4 import sites:
`widget_chat.py:26`, `widget_lead.py:20`, `widget_config.py:23`, `twilio_webhooks.py:238`. Run
`backend/tests/test_widget_api.py` + `test_lead_enrichment.py` to verify.
**Impact:** Reduces blast radius of lead capture bugs. Cuts widget_helpers.py below 1,350L. Next audit
HIGH becomes resolved. Makes future lead-capture features safer to write.
**Category:** code_health

---

### Idea 3: Spec-to-Implementation Symbol Validation Gate in feature-build Skill
**Evidence:** `docs/dev-knowledge/bug-patterns.md` Apr 15: two distinct spec-drift bugs on the same day —
(1) `ExtractorError` in spec but `ValueError` raised in production code; (2) `session_id` dedup path in
spec but `leads` table has no `session_id` column (join path is `leads.conversation_id →
conversations.session_id`). Both would have been caught in <60 seconds by
`python -c "from backend.services.structured_extractor import ExtractorError"` and
`grep -r "session_id" migrations/`. Bug-patterns.md prevention section explicitly says: "MUST run
python -c ..." and "grep migrations OR query Supabase to confirm column exists."
**Action:** Update `.claude/skills/feature-build/SKILL.md` — add mandatory pre-build step: for each
`from <module> import <symbol>` in the spec, run the import check; for each `.eq("col", val)` in the
spec, grep migrations to confirm column; block progress until all checks pass.
**Impact:** Prevents entire spec-drift bug class. Two bugs in one day = systemic gap. Each prevented
bug saves ~2h debugging + spec rewrite.
**Category:** workflow

---

### Idea 4: Small Business SaaS KB Category Seed — 3 Foundational Articles
**Evidence:** `knowledge-base/INDEX.md` — "Small Business SaaS: No articles yet." This category covers
churn, PLG, pricing, vertical SaaS trends — the psychological and economic reasons customers buy and
stay. 16 competitor articles exist but zero SMB customer-behavior articles. `current-tasks.md` shows
launch-readiness rubric at 114/262 NO-GO (56% fail). Customer-gaps.md has "Custom automation
templates" and "AI-to-human handoff" as open critical gaps. KB-first rule: every future session that
needs SMB insight finds nothing.
**Action:** `/kb-discover` targeting 3 queries: (1) "SaaS churn patterns small business under $500/mo",
(2) "product-led growth vs sales-led for vertical SaaS", (3) "pricing benchmarks SMB AI tools 2026."
Compile 3 wiki articles with mandatory "Relevance to AgentNexLiFy" section.
**Impact:** Fills the largest KB knowledge gap. Arms product and pricing decisions with evidence.
Compounds: future sessions stop re-doing this research from scratch.
**Category:** operational

---

### Idea 5: Targeted QA Sprint — Top 3 Unverified Production Commits
**Evidence:** `docs/daily-logs/current-tasks.md` P1: "QA service-layer extraction (ff293f4)" and
"QA scheduled_jobs split (5f3305a)" are TODAY's top priorities (carried from Apr 17). Both commits
touch production paths with zero test coverage of the new split. `scheduled_jobs.py` was 2,024L
split into 5 modules. `branding_service.py` / `faq_service.py` / `conversations_service.py` extracted.
Launch-readiness 114/262 NO-GO. Architecture audit: `managed_agents.py` has `time.sleep` in async paths.
**Action:** Write and run a QA plan for 3 commits: (1) service-layer extraction — run
`python -m pytest backend/tests/test_branding*.py -x -q`; (2) scheduled_jobs split — trace 5 new
modules + `python -m pytest backend/tests/ -k "sched" -x -q`; (3) async sleep audit —
grep `time.sleep` in `managed_agents.py`, confirm caller chain async/sync.
**Impact:** Unblocks P1 backlog. Prevents production incidents from untested splits. Addresses
top priority from current-tasks.md. Moves 3 items to DONE.
**Category:** code_health / operational
