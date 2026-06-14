# Ideas — 2026-06-04 (Run 49)

## Evidence Digest

Zero production code commits in 4 days (run 47 on 2026-06-02 was last real code). Only nightly log writes and subconscious artifacts. Item A (Check 10) blocked by exactly 5 JSX em-dash violations — nightly 2026-06-03 confirmed same 5 files and explicitly called out "fix em dashes in 5 UI files → unblocks Item A." Item D (lead-qualifier-eval.yml) fully implemented (nightly 42992fa). Item B (check-widget-sync.sh) MISSING but widget copies currently in sync. billing.py:263 still missing 15000→autopilot and 25000→professional. email_sequences.py still 1255L. Moratorium day 34, 13 pending items, oldest 48 days. Run 48 combined Items A+B (~25 min) — zero implementation in 24h. Pattern: each bundled or larger recommendation goes unimplemented; the bottleneck appears to be total commitment time, not individual task complexity.

---

### Idea 1: Fix exactly the 5 JSX em-dash lines (Items A — micro-scope, ~2 min)

**Evidence:** `check_project_invariants.py` exits 1 on 5 UI string literals containing `—`. Nightly 2026-06-03 log: "Fix em dashes in 5 UI files → unblocks Item A." personality.md explicitly bans em-dashes. These are UI strings, not logic. Each is a 1-character substitution. Autonomous chain (4226ef4) primed to auto-wire Check 10 the moment invariants exits 0.

**Action:** In 5 JSX files, replace `—` with `-` (or remove the dash entirely for grammatical correctness):
- `frontend/src/pages/IntegrationsPage.jsx:1018`
- `frontend/src/pages/SettingsInboundChannels.jsx:220-221`
- `frontend/src/pages/settings/MessagingSettingsCards.jsx:263/276`

Commit. Nightly fires Check 10 at 2:37 AM.

**Impact:** Closes Item A. Check 10 auto-wired tonight. ~2 min human effort — smallest possible action in the pending queue. Leaves Item B separate for tomorrow's nightly or next interactive session.

**Category:** code_health

---

### Idea 2: Execute Items A+B in single commit (run 48 repeat, ~25 min)

**Evidence:** Same as run 48. Both items known, scripts pre-written in prior winning-concepts. check-widget-sync.sh MISSING, widget copies currently in sync.

**Action:** Fix 5 em-dashes + create check-widget-sync.sh + wire pre-push + fix CLAUDE.md Invariant #4. One commit closes two moratorium items.

**Impact:** Closes Items A and B simultaneously. Triggers Check 10 tonight. Drops pending by 2.

**Category:** code_health / workflow

---

### Idea 3: AI-to-Human Handoff v1 implementation sprint (oldest pending, ~1 day)

**Evidence:** Run 4, day 49, Critical gap for all 7 industries. os_outbound_mirror.py (PR #188, merged May 27) handles SMS/email delivery — reduces scope from ~3 days to ~1 day. customer-gaps.md: Critical impact, Medium effort. Infrastructure: conversations table, Twilio, os_outbound_mirror.send_sms(), handoff_requests table (needs migration).

**Action:** Trigger detection in `widget_chat.py` → write to `handoff_requests` table (migration) → call `os_outbound_mirror.send_sms()` to notify owner → set lead status `needs_follow_up`.

**Impact:** Closes oldest pending item (49 days). Fills Critical gap across all 7 vertical industries. Direct revenue impact: tenants currently lose complex queries that exceed widget AI capability.

**Category:** customer_value

---

### Idea 4: email_sequences.py god-class split via /god-class-splitter (~2h)

**Evidence:** email_sequences.py confirmed 1255L (wc -l above). 3 clean concerns: CRUD (list/get/create), enrollment (start/stop/status), processor (run_sequence_processor, process_sequences). god-class-splitter SKILL.md exists (e848b87). post-split-test-repair SKILL.md exists (d481799). GH #112 N+1 fix becomes easier post-split.

**Action:** Invoke `/god-class-splitter` on `backend/routers/email_sequences.py` — split into `email_crud.py` + `email_enrollment.py` + `email_processor.py`.

**Impact:** Clears 1255-line god class. Enables GH #112 N+1 fix (ROI 2.3). All 3 prerequisites now met for the first time.

**Category:** code_health

---

### Idea 5: Zapier API key plan_status security enforcement (GH #107, ~1h)

**Evidence:** GH #107 filed 2026-04-30 (49 days open). `backend/services/zapier_auth.py::_get_api_key_client` resolves API keys without checking `plan_status`. Cancelled tenants with un-revoked keys bypass tier gate entirely. Parking lot ROI 2.5 (highest in lot). Security gap — not moratorium-gated. Known fix: add `plan_status IN ('active','trialing')` filter + regression test.

**Action:** Add plan_status filter to `zapier_auth.py::_get_api_key_client`. Add `backend/tests/test_zapier_auth.py` regression test. ~1h.

**Impact:** Closes security gap. Prevents cancelled tenants bypassing paid features. Moratorium-exempt (security). Highest ROI item in parking lot at 2.5.

**Category:** code_health / security
