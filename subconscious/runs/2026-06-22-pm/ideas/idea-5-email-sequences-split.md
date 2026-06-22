### Idea 5: Invoke /god-class-splitter on email_sequences.py (1143L → 3 modules)

**Evidence:**
- email_sequences.py is 1143L (down from 1255L after prior fixes), active_direction since run 35 (65+ days pending).
- god-class-splitter SKILL.md ready (e848b87). post-split-test-repair SKILL.md ready (d481799).
- Both moratorium-override bugs now resolved — human capacity exists for M-effort work.
- GH #112/#113 (N+1 queries: 1001 queries per 1000 enrollments) easier to fix post-split.
- 3 clean concerns already identified: email_crud + email_enrollment + email_processor.
- Rule 9: "Don't extend god classes — factor them out. >600 lines = stop."

**Action:**
1. Run `/god-class-splitter` on `email_sequences.py`
2. Split into `email_crud.py` + `email_enrollment.py` + `email_processor.py`
3. Run `/post-split-test-repair` to fix stale @patch targets
4. Verify all tests pass

**Impact:**
- Reduces blast radius of email changes (3 independent modules vs 1 god class)
- Unblocks N+1 query fixes (GH #112/#113)
- ~2h human implementation using the skill

**Category:** code_health
