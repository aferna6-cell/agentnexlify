# Ideas — Run 38 (2026-05-28-pm)

5 candidates generated from evidence gathered this run.

---

### Idea 1: AI-to-Human Handoff v1 — leverage Agent OS outbound infrastructure

**Evidence:** PR #188 (Agent OS rehaul, Groups A+B+C) merged 2026-05-27 — `backend/services/os_outbound_mirror.py` now handles SMS/email/Facebook outbound with replay protection (migration 130, `os_outbound_log` table). `backend/services/os_inbound_bridge.py` manages bridge configs. Run 4 winner (2026-04-16) is 42 days pending. `docs/dev-knowledge/customer-gaps.md` marks AI-to-Human Handoff Critical for all 7 industries. Before PR #188, handoff required building Twilio plumbing from scratch (~3 days). After PR #188, `os_outbound_mirror` handles the delivery layer with 152 tests. Scope reduced to routing decision + trigger detection (~1 day).

**Action:** Hook `backend/routers/widget_chat.py` to detect explicit handoff triggers ("talk to someone", "call me", "need a human") → write to new `handoff_requests` table → call `os_outbound_mirror.send_sms()` or `send_email()` to notify business owner → widget sends acknowledgment to user. Read-only integration with existing os_outbound_mirror interface — no modifications to Agent OS code.

**Impact:** Closes 42-day Critical gap across all 7 industries. Competitive differentiator vs GoHighLevel. Enables autopilot tier upsell scenario. Moratorium parallel-track authorized by run 29.

**Category:** customer_value

---

### Idea 2: billing-constant-guard pre-commit Check 11 — human-session execution (run 37 re-recommendation)

**Evidence:** Run 37 winner (2026-05-28 AM, `033fc3b`). `AMOUNT_TO_PLAN` confirmed missing `15000→autopilot` and `25000→professional` via direct `grep`. Nightly review `dc5ef8e` (2026-05-28) did NOT implement — log file added, pre-commit unchanged. Autonomous channel has now failed twice consecutively (runs 36+37).

**Action:** Human adds 10-line bash block to `scripts/hooks/pre-commit` — code ready in `subconscious/runs/2026-05-28/winning-concept.md §Step 1`. Three-minute task.

**Impact:** Systemic guard against billing constant drift on every commit. WARNING mode — does not block development. Survives GH #181 fix. Same pattern as Check 5 (migration numbers, added by `72f8204`).

**Category:** code_health

---

### Idea 3: post-split-test-repair SKILL.md — human-session creation (run 36 winner)

**Evidence:** 3 occurrences in 6 days: `5f2cd2b` (local_seo import repair after split), `4afb3cf` (stale `@patch` target repair after god-class split), `bca2082` (PostgREST `.filter()` mock repair after API migration cleanup). 100% recurrence rate — every split or API refactor requires test repair. 29 backend + 25 frontend files still exceed 600L per `plans/god-class-refactor_plan.md`. `god-class-splitter` SKILL.md ready. `email_sequences.py` split next in queue.

**Action:** Create `.claude/skills/post-split-test-repair/SKILL.md` using the 8-step checklist already written in `subconscious/runs/2026-05-27/winning-concept.md`. Pure markdown, zero code risk, ~5 min.

**Impact:** Prevents post-split test breakage on every future god-class split. 54 files in backlog plan. ~20 min saved per split = ~18 hours of saved repair work over the full backlog.

**Category:** workflow

---

### Idea 4: Invoke /moratorium-sprint — Items A/B/D (standing action)

**Evidence:** `moratorium-sprint` SKILL.md exists (`7985fbb`). Items A (check_project_invariants pre-commit, ~5 min), B (widget sync guard scripts/check-widget-sync.sh, ~15 min), D (lead-qualifier-eval.yml CI, ~20 min) all MISSING for 24+ days. Agent OS Groups A+B+C shipped — human has bandwidth for context switch. Moratorium exit condition: pending ≤ 2. After sprint: true pending 4→2 = moratorium exits.

**Action:** Invoke `/moratorium-sprint` in current interactive session (~40 min total).

**Impact:** Moratorium exits after 24+ days of active status. Unlocks free-choice recommendations from run 39. Closes 3 long-standing operational items simultaneously. First post-moratorium winner can be Zapier security fix (GH #107, ROI 2.5).

**Category:** workflow

---

### Idea 5: email_sequences.py god-class split — first production use of /god-class-splitter

**Evidence:** `wc -l backend/routers/email_sequences.py` = 1255 lines (unchanged). Run 35 winner (2026-05-26-pm). 3 clean concerns: CRUD (~lines 1-400), enrollment (~lines 400-800), processor (~lines 800-1255). `god-class-splitter` SKILL.md created by nightly review `e848b87`. GH #112 (N+1 `list_enrollments`: 1001 queries/1000 enrollments) and GH #113 (120-line duplication in `_process_pending_sends`) both cleaner post-split.

**Action:** After GH #181 fix (~15 min), invoke `/god-class-splitter email_sequences.py` in interactive session.

**Impact:** 1255-line god class → 3 focused modules. Validates god-class-splitter skill in production. Unblocks GH #112/#113 N+1 fixes. Reduces blast radius of future email automation changes.

**Category:** code_health
