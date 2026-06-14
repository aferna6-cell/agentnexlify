# Ideas — Run 39 (2026-05-29)

## Evidence Base

Commits since run 38 (3 days):
- `061582c` — nightly-commit-review 2026-05-29: **implemented billing-constant-guard Check 11** in scripts/hooks/pre-commit (22 lines added). Run 37 winner DONE. 4th autonomous nightly implementation.
- `3af4626` — subconscious run 38 artifacts
- `033fc3b` — subconscious run 37 artifacts
- `dc5ef8e` — nightly-commit-review 2026-05-28 (did NOT implement post-split-test-repair)

Key state checks:
- Check 11 fires WARNING correctly: `AMOUNT_TO_PLAN missing entries: 15000 25000`
- AMOUNT_TO_PLAN (billing.py:263) still missing 15000→autopilot + 25000→professional
- email_sequences.py = 1255L (run 35 winner, unimplemented day 3+)
- `.claude/skills/post-split-test-repair/` = MISSING (run 36 winner, unimplemented day 2)
- Moratorium Items A/B/D = MISSING (day 26+)
- Nightly review 2026-05-29 log lists post-split-test-repair as Standing Action #5

Governance correction applied: run 37 (billing-constant-guard Check 11) status: pending_approval → implemented (061582c, 2026-05-29). runs_implemented 8→9.

---

### Idea 1: Create post-split-test-repair SKILL.md
**Evidence:** run 36 winner still missing. bca2082 (2026-05-28) confirmed 3rd test-repair instance (API cleanup migration). Nightly review 2026-05-29 explicitly listed it in Standing Actions. 061582c proves autonomous channel IS active today (Check 11 implemented). Pattern: nightly review implements pending LOW-risk .md files it's been made aware of.
**Action:** Create `.claude/skills/post-split-test-repair/SKILL.md` — 8-step checklist for repointing stale @patch targets and imports after module splits. Mark AUTONOMOUS-EXECUTABLE in winning-concept for nightly review.
**Impact:** Unblocks email_sequences.py split (run 35 winner, 1255L). Prevents 2-3 extra repair commits on every future split (29 backend + 25 frontend files in god-class-refactor_plan.md remaining). 5 min effort. Autonomous.
**Category:** workflow

---

### Idea 2: Invoke /god-class-splitter on email_sequences.py
**Evidence:** email_sequences.py confirmed 1255L (run 35 winner, 3+ days). god-class-splitter SKILL.md created (e848b87). 3 concerns confirmed: CRUD/enrollment/processor. GH #112/#113 N+1 queries simpler post-split.
**Action:** Invoke `/god-class-splitter email_sequences.py` to split into email_crud.py + email_enrollment.py + email_processor.py.
**Impact:** Reduces largest non-split backend file. Closes N+1 path to GH #112/#113. ~2h human execution.
**Category:** code_health

---

### Idea 3: handoff_requests migration only (AI-to-Human Handoff partial)
**Evidence:** Run 38 winner (AI-to-Human Handoff v1 via Agent OS), 43+ days Critical gap. os_outbound_mirror.py with 152 tests reduces scope. Moratorium parallel track authorized since run 29.
**Action:** Create ONLY `migrations/131_handoff_requests.sql` — additive new table, no code changes.
**Impact:** DB foundation for AI-to-Human Handoff. 15 min. Parallel track.
**Category:** customer_value

---

### Idea 4: Billing Constants Contract Tests (run 30 winner, 7+ days)
**Evidence:** Run 30 winner recommended `backend/tests/test_billing_constants.py` with parametric assertions. AMOUNT_TO_PLAN still missing 15000+25000. Check 11 (WARNING-only) doesn't block CI. Parametric tests would fail CI until GH #181 fixed — stronger forcing function.
**Action:** Create `backend/tests/test_billing_constants.py` parametric assertions for all 5 plans × current prices. Wire into pr-check.yml.
**Impact:** Would fail CI immediately, forcing GH #181 fix. 20 min effort. But creates CI noise.
**Category:** code_health

---

### Idea 5: Invoke /moratorium-sprint (Items A/B/D)
**Evidence:** check_project_invariants.py still not in pre-commit (Item A). scripts/check-widget-sync.sh still MISSING (Item B). .github/workflows/lead-qualifier-eval.yml still MISSING (Item D). moratorium-sprint SKILL.md exists (7985fbb). Moratorium day 26+.
**Action:** Invoke `/moratorium-sprint` in current interactive session.
**Impact:** Executes 3 S-effort items (~40 min). Pending drops toward moratorium exit condition (≤2).
**Category:** workflow
