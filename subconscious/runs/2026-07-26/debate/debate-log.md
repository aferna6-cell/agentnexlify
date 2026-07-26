# Run 103 Debate Log — 2026-07-26

Top 3 debated: Idea 1 (Step 9H), Idea 3 (Keys Koffee), Idea 5 (email auth failures).

---

## Round 1: Idea 1 — Step 9H Nightly GH Actions Spending-Limit Heartbeat

### Challenge
**Objection A — AUTOPILOT_GH_TOKEN is expired (GH #399).** If the token needed to post the GH #500 comment is the same expired token, Step 9H can't post the comment either. The mechanism breaks at the auth layer before it does any useful work. This is the same failure mode that killed the autopilot loop.

**Objection B — Step 9G already will fail and comment on #403.** When KB goes stale (7+ days), Step 9G fires, `gh workflow run` fails due to #500, and Step 9G already comments on #403 with "GH #500 spending limit as candidate cause." We already have a signal path. Step 9H adds a second signal path on a different issue. Signal duplication without new information.

**Objection C — SKILL.md real estate accumulation.** Steps 9A through 9G are already 19 occurrences in the nightly SKILL.md. Adding 9H without merging the existing Step 9G first means the branch carries 20+ Step occurrences while none of them are active on main. Adding more before merging dilutes the urgency to merge.

### Defense
**Answer A:** AUTOPILOT_GH_TOKEN is expired for the autopilot loop's issue-creation and pr-creation actions. Nightly's GH comment mechanism uses `gh issue comment` — the nightly runner may have separate GH credentials. But Objection A is partially valid: if the nightly runner's GH token is also expired or spending-limited, the comment silently fails. Mitigable by checking gh auth status before attempting the comment, logging the failure, and proceeding. Step 9H's value is in the diagnostic log even if the comment fails.

**Answer B:** Step 9G's #403 comment only fires when KB is stale (>7 days). KB is currently fresh (3 days). Step 9H would fire on EVERY nightly where GH Actions are dark — it's a more aggressive heartbeat. But the objection holds: the signal path already exists via Step 9G. Step 9H is incrementally better, not transformatively so.

**Answer C:** Valid. The branch is carrying Steps 9A-9G (7 occurrences of "Step 9G"), not yet on main. Adding 9H while 9G is unmerged compounds the branch debt. The right sequencing is: merge 9G first, then add 9H in the next cycle.

### Verdict: SURVIVES but weakened
Step 9H is a real improvement but the timing is wrong — adding it before 9G merges increases branch debt. The AUTOPILOT_GH_TOKEN auth concern is real. Net: Step 9H should be parked in the backlog until PR #577 merges.

---

## Round 2: Idea 3 — Keys Koffee Silent Widget Diagnostic GH Issue

### Challenge
**Objection A — No data access = no diagnosis.** The subconscious can't query Supabase from this context. The GH issue would be a checklist without verified findings — a human still has to do all the investigative work. This is a nudge, not a diagnostic.

**Objection B — Widget silence could mean the embed is removed, not broken.** Keys Koffee may have removed the widget embed from their site. A 39-day silence with no error logs could simply mean they deactivated the widget client-side. Filing a "diagnostic" issue implies the widget is broken when it may be intentionally unused.

**Objection C — Low subconscious value.** Creating a GH checklist issue is something any team member can do in 5 minutes. The subconscious improvement loop exists to compound automated quality improvements, not to file manual investigation checklists that require human execution for every step.

### Defense
**Answer A:** Partial. The issue would include WHERE to look (specific DB queries, table names, column names, tenant_id lookup). It reduces friction for human investigation from "I wonder where to start" to "run these 4 specific queries." Still valid even without pre-verified findings.

**Answer B:** Strong objection. Widget silence is not necessarily broken. If the embed was intentionally removed, filing a "silent widget" issue wastes human attention on a non-issue. Distinguishing "removed embed" from "broken widget" requires Supabase access or site audit.

**Answer C:** Valid. A GH checklist issue for a single tenant's widget silence is below the compounding threshold for the subconscious. Better suited for a morning digest action item or a human spot-check than a subconscious recommendation cycle.

### Verdict: ELIMINATED
Objection B is disqualifying — the premise ("widget broken") may be wrong. Objection C shows this is below the improvement loop's leverage threshold.

---

## Round 3: Idea 5 — email_sequences Auth Test Failures Classification GH Issue

### Challenge
**Objection A — "Pre-existing" was already the verdict.** The nightly reviewer (run ab1a7c2 review) already verified these failures reproduce on pre-split HEAD and are not regressions. Filing a GH issue to "classify" them re-investigates something already investigated. If they were a real auth bug, the nightly reviewer would have flagged them as MEDIUM/HIGH, not CLEAN.

**Objection B — Auth fixture failures are known technical debt, not unknown risk.** The email_sequences suite has auth fixtures that aren't properly set up for test environments. This is a known pattern in the codebase (other router suites have the same issue per GH #394 notes). Filing one more "fix auth fixtures" issue doesn't compound the automation — it adds to an already-long queue.

**Objection C — 8 tests in an email suite are not blocking production.** The backend ships from Railway; CI is dark due to GH #500. These test failures are not preventing shipping. Prioritizing them during a period when GH Actions is spending-limited adds work to a queue that can't be executed until #500 is resolved.

### Defense
**Answer A:** The nightly reviewer labeled them CLEAN (not regressions) but didn't classify whether they're (a) test fixture issues safe to ignore or (b) real auth path bugs masked by the fixture. That distinction matters. If (b), they represent silent production risk. A GH issue forces the classification to happen with human eyes.

**Answer B:** Valid. "Auth fixture" issues are a known pattern. But the email_sequences split (1143 lines → 3 files) changed the import structure. The split may have exposed fixture wiring issues that didn't matter when everything was in one file. A targeted GH issue on THIS suite is different from the general auth fixture problem.

**Answer C:** Partially valid, but weak. Tests failing in CI is a quality debt that compounds regardless of whether CI is currently running. When #500 is resolved, all CI runs; if these tests are failing, they block green CI. Filing the issue now means the fix is queued and ready.

### Verdict: SURVIVES but lower priority than Idea 4
The objections partially hold. Filing a classification GH issue is legitimate but Idea 4 (Managed Agents Phase 0 kickoff) has higher leverage: it unblocks the next product growth lever vs. cleaning up 8 test fixtures.

---

## Synthesis

**Eliminated:** Idea 3 (Keys Koffee — premise may be wrong, below leverage threshold)
**Parked:** Idea 1 (Step 9H — right idea, wrong timing; add after PR #577 merges)
**Survive:** Idea 5 (email auth), Idea 4 (Managed Agents Phase 0), Idea 2 (fastapi cap)

**Head-to-head: Idea 4 vs Idea 5**
- Idea 4 (Managed Agents Phase 0): Unblocks next growth lever. Environment provisioning + env vars + smoke test = actionable in one session. 0 existing tracking. High urgency (rollout plan was created but nothing started).
- Idea 5 (auth failures): Important but lower urgency. CI is dark; the failures can't be caught until #500 resolved anyway. Classification can wait.

**Winner: Idea 4 — Managed Agents Phase 0 Kickoff GH Issue**

Rationale: The rollout plan exists, the registry code exists (`managed_agents_registry.py` references `MANAGED_AGENTS_ENVIRONMENT_ID`), but no tracking issue pushes Phase 0 forward. Every day without a Managed Agent endpoint active is a day the product's differentiating AI layer stays at 0 revenue. Concrete, 3-step kickoff issue that unblocks the next growth cycle.

**Runner-up backlog:** Idea 5 (file after #500 resolved), Idea 1 (file after #577 merged), Idea 2 (file when fastapi 0.136 actually releases on PyPI).
