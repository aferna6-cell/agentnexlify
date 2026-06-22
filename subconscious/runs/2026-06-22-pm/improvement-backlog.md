## Run 2026-06-22-pm — Improvement Backlog

### Winner (this run)
- **Check 7: Plan-Catalog Drift Guard** — AUTONOMOUS-EXECUTABLE. ~15 lines in `scripts/check_project_invariants.py`. Pre-condition met (57f2bb4 + 29ed1d4 landed). Moratorium exits this run.

---

### Priority 1 — AI-to-Human Handoff v1 (Bonus A)
**Source:** Idea 2, run 2026-06-22-pm. Customer-gaps.md: Critical, all 7 industries.
**Estimated effort:** 1–1.5 day human implementation.
**Action:** Trigger detection in `widget_chat.py` → `handoff_requests` table → `os_outbound_mirror.send_sms()` + `.send_email()` → conversation status "handoff_pending".
**Blocking:** Nothing (moratorium exits this run).
**Why urgent:** GoHighLevel "AI Employee" is primary competitor moat. Every week without this is trials we lose. 65+ days pending (Run 4 original recommendation).

---

### Priority 2 — Migration Coverage Script
**Source:** Idea 3, run 2026-06-22-pm. `docs/dev-knowledge/migration-triage-2026-06-22.md`.
**Estimated effort:** ~2h implementation.
**Action:** `scripts/check_migration_coverage.py` — parse each `migrations/NNN_*.sql` for DDL targets, query `information_schema` on Supabase, output migrations whose objects genuinely don't exist.
**Blocking:** Supabase MCP credentials at script runtime.
**Why useful:** GH #263 false-positive alarm is a chronic distraction. GH #329 opened for an already-applied migration. Eliminates recurring triage burden.

---

### Priority 3 — Billing Agent-Run Caps Product Decision
**Source:** Idea 4, run 2026-06-22-pm. `billing_reconciliation.py:55`.
**Estimated effort:** Product decision (not autonomous). ~30min implementation after decision.
**Action:** Confirm agent-run caps for chatbot + agent_os (proposed: chatbot=200, agent_os=1500). Add to `billing_reconciliation._PLAN_AGENT_RUN_CAPS`. Mirror in `usage_meter.PLAN_AGENT_RUN_CAPS`. Remove "pending product decision" comment.
**Blocking:** Product decision required.
**Why useful:** Every paid tenant since 2026-06-16 gets wrong overage reports.

---

### Priority 4 — Email Sequences God-Class Split
**Source:** Idea 5, run 2026-06-22-pm. `email_sequences.py` at 1143L.
**Estimated effort:** ~2h human implementation using skills.
**Action:** `/god-class-splitter` on `email_sequences.py` → `email_crud.py` + `email_enrollment.py` + `email_processor.py`. Then `/post-split-test-repair` to fix stale @patch targets.
**Blocking:** None (both skills ready: e848b87, d481799).
**Why useful:** Reduces blast radius of email changes. Unblocks GH #112/#113 N+1 query fixes (1001 queries per 1000 enrollments).
**Note:** This was an active_direction as pending_approval; now both blocking items (GH #308, GH #292/#293) are implemented. Can be re-recommended in a future run if no progress.

---

### Governance notes (run 2026-06-22-pm)
- Moratorium exiting: GH #308 + GH #292/#293 both implemented. pending_approval → 0. moratorium_active → false.
- Moratorium has been active since run 15 (2026-05-11), now 44+ days. Exit is significant — all categories now unblocked.
- Next high-value recommendation: AI-to-Human Handoff (1.5 day human effort, Critical gap).
