### Idea 2: Wire Check 10 in WARNING Mode — Break the Exits-0 Deadlock

**Evidence:** Check 10 (check_project_invariants.py) has been `pending_autonomous` since run 22 (day 55+). The exits-0 pre-condition has failed 6+ times as new PRs (a5c65b5, 7c8825c) introduce violations between nightly cycles. Check 11 and Check 12 were both wired in WARNING mode — neither blocks commits, both provide signal. 7c8825c introduced `from __future__` + 10 em-dashes that slipped past Check 2 (hooks not installed in the commit environment), suggesting the root problem is execution-environment gaps, not script correctness.

**Action:** Add Check 10 to `scripts/hooks/pre-commit` in WARNING mode (echo warning, increment WARNINGS, do not exit 1). Remove the exits-0 pre-condition gate in nightly SKILL.md for Check 10.

**Impact:** Check 10 activates immediately regardless of current violations. Developers see warnings at commit time. Violations visible in CI on every PR. Can upgrade to FAIL mode once codebase cleans up. Breaks the 55-day deadlock.

**Category:** workflow
