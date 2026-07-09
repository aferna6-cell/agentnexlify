# Idea 5 — Invoke /god-class-splitter on email_sequences.py (run 41, M-effort, moratorium)

**Score:** 5.5 / 10
**Effort:** M (~2 hours, human required)
**Category:** code_health
**Autonomous:** NO
**Moratorium:** BLOCKED

## Evidence

- email_sequences.py: ~1143L (last measured run 62, some trimming since run 41's 1255L)
- Run 41 winner (2026-05-30) — never implemented
- god-class-splitter SKILL.md exists (e848b87)
- post-split-test-repair SKILL.md exists (d481799)
- GH #112/#113: N+1 query bugs easier to fix post-split
- Both prerequisites met for first time at run 41 (skills ready)

## Why it doesn't win run 66

- Moratorium active — M-effort, human required, adds to pending rather than reducing it
- No new forcing function (run 41 still pending, no regression or new bug since then)
- Correct sequence: clear run 65 (widget/em-dash) + run 65 mandate escalation FIRST, then address email_sequences
- Pre-commit Check 13 blocking all commits — even if split were started, commits would be blocked until run 65 lands

## Promotion path

Run 67+ candidate once:
1. Run 65 lands (check exits 0)
2. Run 66 trigger instruction SKILL.md edit delivered
3. Moratorium exits (pending ≤ 2)

At that point email_sequences.py split becomes the highest-ROI code_health item after cleanup sprint.
