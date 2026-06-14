# Debate Log — 2026-04-30 (Run 9)

Moratorium active. Top 3 ideas debated (ranked by age / urgency).

---

## Idea 1: JS Silent Catch Pre-commit Guard (Run 3)

### Challenge
**C1: Is this still the right priority after 19+ days?**
If it mattered, someone would have shipped it. Maybe the violations are acceptable graceful degradation — `.catch(() => null)` on optional SEO history fetch might be fine intentionally.

**Defend 1:** Both violations are NOT intentional graceful degradation. `MarketingDashboardPage.jsx:96` swallows analytics fetch errors silently — users see an empty chart with no indication something went wrong. `LocalSEOPage.jsx:262` swallows SEO audit history silently. Same root cause class as the noshow_recovery CAN-SPAM bug (2026-04-23): defensive exception swallowing that obscures real outages. Pre-commit covers Python bare-except for exactly this reason.

**C2: Is the highest-leverage use of run 9 a code_health guard, or should it be customer_value?**
AI-to-Human Handoff (run 4) is Critical for all 7 industries. Why not that?

**Defend 2:** Moratorium protocol is explicit: implement oldest pending winner. JS Silent Catch is oldest (day 19+). The moratorium exists precisely because skipping implementation in favor of "higher leverage" ideas is what caused 5 pending winners in the first place. The pattern must break.

**C3: What if the guard creates false positives?**
Legitimate `.catch(() => null)` patterns (e.g., optional background prefetch) would block commits unnecessarily.

**Defend 3:** Risk is real but manageable. Solution: add an inline disable comment pattern (e.g., `// subconscious: ok-silent-catch`) to allow exceptions. Precedent: ESLint `// eslint-disable-next-line`. Pre-commit can grep for the override comment before flagging. Same approach the Python bare-except check uses (check comment on next line).

**C4: Implementation difficulty?**
Pre-commit is a bash script. Adding grep for JS `.catch` patterns is S-effort. Tested via synthetic violation + revert.

**Defend 4:** Pre-commit already does multi-language checks (Python + bash). Bash grep on `*.js` and `*.jsx` staged files is 5-10 lines. Exactly the same mechanism as the existing Python checks at lines 80-130.

### Verdict: **SURVIVES** — oldest pending, violations confirmed, S-effort, moratorium protocol requires it

---

## Idea 2: AI-to-Human Handoff v1 (Run 4)

### Challenge
**C1: Moratorium protocol picks oldest. Run 4 is not oldest.**
Run 3 is older. Moratorium says oldest. This idea loses on protocol alone.

**Defend 1:** Protocol overrides impact ranking in moratorium. There is no defense that makes run 4 the right pick over run 3 while moratorium is active.

**C2: M-effort (1.5-2 days) vs S-effort alternatives.**
Even if the protocol allowed flexibility, M-effort items are harder to close quickly. Choosing M-effort while the backlog has 4+ S-effort items compounds lag.

**Defend 2:** The effort argument is valid — but the effort argument also applies in parking lot. Deferred correctly.

**C3: Has evidence strengthened since run 4?**
customer-gaps.md unchanged. No new customer feedback. No new urgency signal.

**Defend 3:** No new urgency evidence. Parking lot hold is correct.

### Verdict: **WEAKENED → parking lot** — right idea, wrong order; moratorium protocol + M-effort both cut against it

---

## Idea 3: Widget 3-Copy Sync Guard (Run 7)

### Challenge
**C1: Run 7 winner is 6 days old. Run 3 is 19+ days. Moratorium protocol picks oldest.**
No argument changes this ordering.

**Defend 1:** Correct. Run 7 is deferrable until run 3 clears.

**C2: Is there any urgency signal that makes run 7 jump the queue?**
No new widget deploys. No reported drift between the 3 copies. No production incident from widget mismatch since run 7 recommended it.

**Defend 2:** No new urgency. Deferred correctly.

**C3: Would creating the script (S-effort) be easier than implementing the JS catch guard?**
Both S-effort. Order by age — run 3 first.

**Defend 3:** S-effort tie broken by age. Run 3 still wins.

### Verdict: **WEAKENED → parking lot** — correct idea, wrong priority order in moratorium; promote to run 10 winner if run 3 clears

---

## Synthesis Decision

| Rank | Idea | Verdict | Rationale |
|------|------|---------|-----------|
| 1 | JS Silent Catch Guard (run 3) | **SURVIVES → WINNER** | Oldest pending, violations confirmed, S-effort, moratorium protocol |
| 2 | Widget 3-Copy Sync Guard (run 7) | WEAKENED → parking lot | Correct idea, 6 days old vs 19+, promote next |
| 3 | AI-to-Human Handoff v1 (run 4) | WEAKENED → parking lot | M-effort, 14 days, deferred by protocol |
| 4 | Pre-fix em-dash + wire invariants (run 8) | Not debated | 5 days old, has a blocker |
| 5 | Update governance for run 2 (admin) | Not debated | Admin task, folded into governance update this run |

**Winner: JS Silent Catch Pre-commit Guard (Run 3)**
