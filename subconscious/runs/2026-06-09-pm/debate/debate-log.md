# Debate Log — 2026-06-09-pm (Run 53)

Top 3 ideas by impact, each challenged and defended.

---

## Idea 1: os_action_dispatch.py test coverage

### Challenge Round 1
**Is the evidence strong enough?**
"85L with 0 tests" — but `test_os_engine_cutover.py` has 14 tests covering Agent OS Phase 4. Maybe the dispatch layer is already indirectly exercised?

**Defend:**
`test_os_engine_cutover.py` (239L) covers the engine cutover path in `os_thread_runner.py`. It does NOT import or call `queue_action_for_run()` from `os_action_dispatch.py`. Confirmed by reading both files: `test_os_engine_cutover.py` mocks `os_thread_runner.process_incoming_message`, not `os_action_dispatch.queue_action_for_run`. Zero indirect coverage.

### Challenge Round 2
**Is this the highest-leverage thing right now?**
"Fixing kb-autopopulate restores 35 days of competitive intel — arguably higher strategic value."

**Defend:**
`os_action_dispatch.py` handles ALL approved deliverable actions for ALL tenants in production. One silent failure here means a booked appointment confirmation SMS fires twice (duplicate action_type), or never fires (no action_run created). The idempotency guard is the correctness contract. PRs #211 ("Act hardening") and #212 ("research worker") are currently in review — they ADD code paths through this dispatch layer. Test coverage gap compounds every day PRs ship on top of it.

kb-autopopulate is broken but doesn't cause customer harm today — it affects competitive intel quality, not production actions.

### Challenge Round 3
**What could go wrong?**
"Writing tests for 85L of production code is straightforward. Can nightly actually create a test file autonomously?"

**Defend:**
Precedent established: nightly created `.claude/skills/moratorium-sprint/SKILL.md` (7985fbb), `.claude/skills/god-class-splitter/SKILL.md` (e848b87), `.claude/skills/post-split-test-repair/SKILL.md` (d481799). All were new `.md` files. Test files in `backend/tests/` are in scope — same class as `.py` additions documented in nightly scope extension (4226ef4). The implementation sketch provides all 5 mock-based test functions; nightly has enough to execute.

**Verdict: SURVIVES → WINNER**

---

## Idea 2: kb-autopopulate fix (35-day stale KB)

### Challenge Round 1
**Is the evidence strong enough?**
"The log says 'network sandbox denies outbound' — this may be an environment-level constraint (Railway sandbox), not a fixable code issue."

**Defend:**
The log also says "agent-browser not installed." `fill-instructions-before-guessing.md` Rule 1 is directly applicable: "A hook/command references a tool that isn't installed. Fix the hook." The fix is to make `kb-autopopulate.sh` NOT fail silently when agent-browser is absent — fall back to skipping the web-search phase gracefully and still running the compile phase. That's a 10-line bash change, not an environment fix.

### Challenge Round 2
**Is this the highest-leverage thing right now?**
"Tenant KBs are separate from kb-autopopulate. The stale knowledge affects competitive intel, not production AI quality."

**Defend:**
True. The stale KB affects CLAUDE's ability to reason about the competitive landscape in future sessions. This matters for planning (CLAUDE.md §Competitive positioning) but not for runtime tenant widget interactions. The urgency is lower than a production correctness gap.

### Challenge Round 3
**Has this been tried?**
"kb-autopopulate was last working 2026-05-05. Four weeks of nightly reviews haven't fixed it."

**Defend:**
Nightly reviews have not been directed to fix kb-autopopulate. It's outside nightly's autonomous scope (nightly focuses on committed code fixes, not script maintenance). This would need to be a human-executed or explicitly delegated task.

**Verdict: SURVIVES but WEAKENED. Higher-confidence alternative (Idea 1) exists. Park as "Questions for Next Run" if not chosen.**

---

## Idea 3: WordPress plugin spec (GH #214)

### Challenge Round 1
**Is the evidence strong enough?**
"A 24-hour-old GitHub issue with no prior subconscious context — the spec hasn't been justified yet."

**Defend:**
GH #214 is in the morning digest's "5 new roadmap items" batch. The user filed it intentionally. 43% WordPress market share is a real distribution moat. But it's thin evidence for a subconscious winner — one issue filed isn't a pattern.

### Challenge Round 2
**Is this the highest-leverage thing now?**
"WordPress plugin development is L-effort (new repo, PHP/JS plugin, WP marketplace submission). A spec is atomic but the downstream work is large."

**Defend:**
The spec is atomic (one markdown file). But writing a spec for a future L-effort project when production code has unverified correctness is misaligned priority. The moratorium exists because implementation backlogs are high.

### Challenge Round 3
**Similar to rejected path?**
"No. WordPress plugin has never been proposed. But the pattern 'spec a new feature during moratorium' was implicitly rejected in runs 21/29 in favor of fixing existing code."

**Verdict: KILLED. Evidence is thin (24h old issue). Production correctness gap (Idea 1) is higher priority. WordPress plugin spec moves to parking lot with ROI 1.8.**

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| os_action_dispatch.py coverage | SURVIVES | WINNER |
| kb-autopopulate fix | SURVIVES (WEAKENED) | Parking lot + next-run question |
| WordPress plugin spec | KILLED | Parking lot ROI 1.8 |
| Integration health probe | Not debated | Parking lot ROI 2.0 |
| Activity log emission | Not debated | Parking lot ROI 1.7 |
