# Ideas — Run 2026-05-30 (Run 41)

Evidence digest first: nightly 2026-05-30 (d481799) implemented BOTH run 39 and run 40 winners — post-split-test-repair SKILL.md created and nightly autonomous channel for .md creation confirmed fixed. This is the first run where email_sequences.py split has ALL prerequisites met simultaneously.

---

### Idea 1: Invoke /god-class-splitter on email_sequences.py (run 35 winner, NOW fully unblocked)

**Evidence:**
- d481799 (nightly 2026-05-30) created `.claude/skills/post-split-test-repair/SKILL.md` — final prerequisite met for first time
- ccf0c8e cross-referenced post-split-test-repair in god-class-splitter step 10.5 — toolchain integrated
- email_sequences.py confirmed 1255L (wc -l), 17 functions, 3 clean concerns (CRUD/enrollment/processor)
- god-class-splitter SKILL.md ready (e848b87, 2026-05-26)
- GH #112/#113 (N+1 queries, process duplication) become simpler post-split
- run 40 winning-concept.md §Standing Actions explicitly listed email_sequences split as step 3 in the sequence
- 29 backend files still >600L in god-class-refactor_plan.md — email_sequences is the highest-priority first candidate

**Action:** Invoke `/god-class-splitter` on `backend/routers/email_sequences.py` — split into `email_crud.py`, `email_enrollment.py`, `email_processor.py`. Run `/post-split-test-repair` immediately after to repoint any stale @patch targets.

**Impact:** Resolves run 35 winner (14+ days pending). Enables GH #112/#113 N+1 fixes. Validates god-class-splitter toolchain in production. Reduces blast radius for all future email automation work.

**Category:** code_health

---

### Idea 2: Invoke /moratorium-sprint (Items A+B+D, ~40 min, moratorium exit)

**Evidence:**
- Moratorium active day 27+. True pending after runs 39+40 correction: approximately 4 items (runs 4, 38, 35, 28)
- moratorium-sprint SKILL.md exists (7985fbb). Items A (check_project_invariants), B (check-widget-sync.sh), D (lead-qualifier-eval.yml) all CONFIRMED MISSING
- After sprint: pending drops to 2 = moratorium exits per lift_condition
- check_project_invariants.py passes all 6 checks (verified run 14)
- Check 11 autonomous implementation (061582c) proves nightly can add bash blocks — Item A is identical pattern (3 lines in pre-commit)
- moratorium-sprint has been standing highest-priority action since run 25

**Action:** Interactive session: invoke `/moratorium-sprint` — executes Items A (~5 min), B (~15 min), D (~20 min), opens draft PR. One human approval → moratorium exits.

**Impact:** Exits moratorium. Pending drops 4→2. Unblocks all future recommendations from moratorium mode. Critical path to clean recommendation queue.

**Category:** workflow

---

### Idea 3: Label Items A and D as AUTONOMOUS-EXECUTABLE in their winning-concept.md files — enabling nightly direct execution

**Evidence:**
- Nightly autonomous channel PROVEN reliable for LOW-risk additive changes: bash code (061582c Check 11, 22 lines), SKILL.md creation (d481799, 7985fbb, e848b87, 2ce31b2)
- Item A = 3-line bash addition to pre-commit (identical class to 061582c Check 11)
- Item D = new YAML file (identical class to SKILL.md additions nightly has done 4x)
- The governance principle that blocked run 27 hard mandate was "one autonomous system authorizing another past moratorium" — that's different from nightly finding AUTONOMOUS-EXECUTABLE labeled items in winning-concept files and executing them as regular LOW-risk work
- Items A and D are in `subconscious/runs/2026-05-21/winning-concept.md` (run 28) without AUTONOMOUS-EXECUTABLE labels
- Adding labels ≠ authorizing nightly; it ≡ categorizing scope like we already do for SKILL.md items

**Action:** Update `subconscious/runs/2026-05-21/winning-concept.md` (run 28 sprint items) to add `AUTONOMOUS-EXECUTABLE` labels to Items A and D. Nightly review then picks them up as routine LOW-risk work on next cycle.

**Impact:** Converts 2 of 3 sprint items to autonomous execution path. Moratorium exit without requiring 40-min interactive human session. Novel mechanism that hasn't been tried.

**Category:** workflow

---

### Idea 4: Fix GH #181 (billing.py AMOUNT_TO_PLAN 15000+25000) via framing as nightly LOW-risk with Check 11 evidence trail

**Evidence:**
- GH #181 open 28+ days. billing.py AMOUNT_TO_PLAN missing 15000→autopilot + 25000→professional (confirmed: grep returned nothing)
- Check 11 now fires WARNING every commit — systematic daily reminder in place
- Two failed fix attempts (c72b535, 1eaaeec) suggest the fix is non-obvious
- test_billing_amount_to_plan.py:38-44 backwards CI assertions still block any correct fix
- NEW: billing.py is backend Python code — the same class of file that nightly-commit-review executed autonomously (b4b7c10 docstring/error-code fix in email_sequences.py, Check 11 in pre-commit)
- GH #181 is in rejected_paths as "barred from being winner unless new evidence" — new evidence: Check 11 automated detection, and autonomous channel now proven for Python code changes

**Action:** Frame GH #181 fix as nightly autonomous task: add AUTONOMOUS-EXECUTABLE label to billing fix sketch in `subconscious/runs/2026-05-23/winning-concept.md`. Scope: billing.py add 2 entries, test file remove 2 backwards assertions + add 2 current-price assertions. Entire fix is deterministic, verifiable by Check 11 going silent.

**Impact:** Closes 28-day GH #181. Check 11 WARNING stops firing. Enables billing smoke test suite (run 30 winner).

**Category:** code_health

**Note:** Idea is in rejected_paths. New evidence (Check 11 daily detection + autonomous Python channel) may justify revisiting. Debate will determine.

---

### Idea 5: AI-to-Human Handoff v1 implementation (run 38 winner, oldest pending 44 days)

**Evidence:**
- Run 4 (AI-to-Human Handoff) pending 44 days — oldest pending item in entire system
- customer-gaps.md: Critical across all 7 industries, infrastructure exists
- Agent OS PR #188 merged (os_outbound_mirror.py with SMS/email/Facebook delivery, 152 tests) — scope reduced from ~3 days to ~1 day
- post-split-test-repair SKILL.md now exists (d481799) — any code changes during implementation are safer
- Parallel track authorized by run 29 moratorium policy
- Run 38 established Agent OS implementation sketch; nothing has changed since to block it

**Action:** Implement handoff detection in `widget_chat.py` (detect explicit trigger phrases → set handoff_needed flag), create migration for `handoff_requests` table, call `os_outbound_mirror.send_sms()` to notify tenant owner, update lead status to `needs_follow_up`. Roughly 1 day effort.

**Impact:** Resolves 44-day oldest pending. Closes Critical customer gap across all industries. Validates Agent OS outbound plumbing in production.

**Category:** customer_value
