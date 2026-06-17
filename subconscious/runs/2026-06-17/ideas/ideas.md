# Ideas — Run 59 (2026-06-17)

Evidence gathered from: git log (3d), nightly review bc91e97, bug-patterns.md, customer-gaps.md, governance.json, live invariant check.

Run 58 winner (Check 13) implemented by nightly bc91e97 this morning. All 13 pre-commit checks active. check_project_invariants.py exits 0. First clean pre-commit state in 46 days.

---

### Idea 1: Fix GH #308 — Webhook Idempotency Retry-Drop Bug
**Evidence:** Nightly bc91e97 (today) filed GH #308: "webhook idempotency early-write drops payment recovery events on handler failure." billing.py:234-247 — `check_and_record` inserts the idempotency key early; if the handler raises an exception (line 280, raises 500 to force Stripe retry), `record_response` (line 285) is never called. On Stripe's retry: `check_and_record` returns `(False, None)` and `if not is_new: return {"status": "ok"}` returns 200 — event silently dropped. PR #301 (47c7f8b, 3 days ago) shipped dunning recovery which depends on `invoice.payment_succeeded`. Same pattern in stripe_webhooks.py.
**Action:** In billing.py:236 and stripe_webhooks.py equivalent: change `if not is_new: return {"status": "ok"}` to `if not is_new and _cached is not None: return {"status": "ok"}`. Add warning log for the fallthrough path (`_cached is None` = prior handler failed, reprocessing). ~10 lines in 2 files.
**Impact:** Prevents silent drop of payment recovery events on transient handler failure. PR #301 dunning recovery now works correctly under DB hiccups. Stripe's 3-day retry window works as designed.
**Category:** code_health
**AUTONOMOUS-EXECUTABLE:** YES — small pattern fix, no schema change, test in test_conversion_funnel.py or new test_billing_idempotency.py.

---

### Idea 2: Fix email_sequences N+1 Queries (GH #112, ROI 2.3)
**Evidence:** GH #112 opened 2026-05-02 (46 days, ROI 2.3). email_sequences.py now at 1143L in backend/routers/. `list_enrollments` makes 1 DB query per enrollment (1001 queries per 1000 enrollments). `list_sequences` makes 2 queries per sequence. Parking lot entry promoted in run 35 debate.
**Action:** Apply bulk `.in_()` queries to `list_enrollments` + `list_sequences` in email_sequences.py. Fetch all enrollment rows in one query, then map in Python. ~30 lines changed. Add regression test.
**Impact:** Linear → O(1) DB calls for email sequence listing. No user-visible bug at current adoption but creates a performance wall at scale. Addresses oldest open performance issue.
**Category:** code_health
**AUTONOMOUS-EXECUTABLE:** Possibly — straightforward query refactor with clear test gates.

---

### Idea 3: AI-to-Human Handoff v1 — Explicit Trigger in widget_chat.py
**Evidence:** customer-gaps.md: "AI-to-Human Handoff — Critical for complex queries — All industries." Oldest pending (run 4, day 62). os_outbound_mirror.py shipped PR #188 (2026-05-27, 152 tests). Landing redesign (021e245, 3 days ago) repositioned as "AI Front Desk / AI Workforce" — handoff is core to the AI Front Desk value prop.
**Action:** Add explicit trigger string detection in widget_chat.py ("talk to human", "speak to someone", "need help now") → write to `handoff_requests` table → SMS owner via `os_outbound_mirror.py`. ~100 lines in widget_chat.py + migration 154.
**Impact:** Fills critical product gap all 7 industry verticals. Directly supports "AI Front Desk" brand positioning. Closes run 4 (oldest pending item, 62 days).
**Category:** customer_value
**AUTONOMOUS-EXECUTABLE:** NO — M-effort, human required.

---

### Idea 4: Split widget_chat.py God Class (1307L → core/session/lead)
**Evidence:** widget_chat.py is 1307L — largest router, 2x the 600L god-class threshold. PRs #254, #301, #307 all touched widget ecosystem in 3 days. Rule 9 threshold triggered. AI-to-Human Handoff (Idea 3) becomes lower-risk after split.
**Action:** Invoke /god-class-splitter on widget_chat.py. Extract `widget_session.py` (session management, ~300L) and `widget_lead_capture.py` (lead handling, ~350L). Remaining `widget_chat.py` core at ~400L. Use post-split-test-repair skill.
**Impact:** Reduces blast radius for every future widget feature. Enables parallel development. Prerequisite for safer AI-to-Human Handoff implementation.
**Category:** code_health
**AUTONOMOUS-EXECUTABLE:** NO — M-effort, human required, active PRs make timing risky.

---

### Idea 5: Fix kb-autopopulate.sh — Restore KB Intelligence Pipeline
**Evidence:** parking lot ROI 1.8. scripts/daily/kb-autopopulate.sh uses `agent-browser` CLI not installed in any environment. KB stale 35+ days. Landing redesign (AI Front Desk positioning) makes fresh competitor/industry knowledge more critical than ever.
**Action:** Replace `agent-browser` invocations with direct `curl`/WebFetch calls. Or add `command -v agent-browser || { echo "agent-browser not installed, skipping"; exit 0; }` guard to prevent silent failure. Restore twice-daily KB auto-population.
**Impact:** Restores KB intelligence feed. KB drives AI response quality for tenant queries. Operational reliability improvement.
**Category:** operational
**AUTONOMOUS-EXECUTABLE:** YES — script edit, no schema change.
