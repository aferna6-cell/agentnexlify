### Idea 4: Finish email_sequences.py split — reduce from 1143L to 3 modules

**Evidence:** Run 41 winner (2026-05-30, pending_approval). cfdd6e3 (2026-06-15) refactored email_sequences.py for N+1 fix — file now 1143L (was 1255L). The N+1 fix extracted `_count_by_sequence_id` and consolidated `_process_pending_sends` — essentially started the split. 3 clean concerns remain: CRUD ops (list/get/create/update/delete), enrollment logic (subscribe/unsubscribe/status), processing pipeline (run_sequence_processor/_process_pending_sends). god-class-splitter SKILL.md exists (e848b87). post-split-test-repair SKILL.md exists (d481799).

**Action:** Invoke /god-class-splitter on email_sequences.py → email_crud.py + email_enrollment.py + email_processor.py. Fix import paths. Run /post-split-test-repair. GH #112/#113 N+1 follow-ups simpler post-split.

**Impact:** Reduces file to ~380L per module. Closes run 41 pending_approval (60+ days). Makes GH #112/#113 N+1 fixes straightforward.

**Category:** code_health
