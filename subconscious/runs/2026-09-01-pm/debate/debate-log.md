# Debate Log — Run 115 (2026-09-01-pm)

## Top 3 Ideas Debated

---

### Idea 1: Step 9L — Nightly Connector Auth Pattern Scan

**Challenge:**
- Evidence is thin: only gmail_connector.py confirmed missing 401 in other connectors. What if the others don't need 401 handling because they use different auth (OAuth2 with auto-refresh, not HTTP Basic)?
- Is this the highest-leverage thing? M8 sprint is the active focus; connector auth is a trailing concern.
- Step 9I (demo-role sweep) worked because the pattern was already proven at org level. Connector auth is subtler — grep for "401" could miss retry logic wrapped differently.

**Defend:**
- Commit 8a60a59 is fresh evidence (2026-08-30). The 101-addition fix on gmail_connector.py confirms auth was broken in production, not theoretical.
- connector_awareness.py (registration) and connector_registry.py (routing) are clearly different concerns; any connector that makes HTTP calls needs 401 handling.
- The grep pattern is conservative: flag files WITHOUT 401/refresh/retry, not flag as broken. Any connector without any of those strings is suspicious enough to warrant a GH issue for human review.
- Step 9I validated the mechanism: grep → file issue → issue-to-pr-loop. Zero infrastructure cost.
- Autonomous-executable (SKILL.md bash block) = no human gate needed, fires on next nightly.

**Verdict: SURVIVES → WINNER**

---

### Idea 2: os_tool_executions.py god-class split issue

**Challenge:**
- run_115_mandate explicitly says "if stable (0 commits 4d+)." File was committed TODAY (2026-09-01). The mandate condition is unmet.
- Filing an issue when the file is actively changing risks the issue becoming stale or wrong immediately.
- Adding a "hold" note to an issue is clutter; future agents/humans will have to parse the condition.

**Defend:**
- Filing now prevents repeated subconscious rediscovery next run.
- "Hold" label on a GH issue is standard practice; issue-to-pr-loop respects labels.
- Effort is XS — negligible cost to create the issue even if it holds.

**Verdict: WEAKENED**
Mandate condition (4d+ stability) is the explicit gate. Deferred to run 116. If file stable by then, file issue at run 116. If not, defer again.

---

### Idea 3: Wire CRM eval to CI

**Challenge:**
- Evidence that CI registration is missing is UNCONFIRMED. The summary only says "evidence of CI registration not confirmed" — that means unread, not confirmed absent.
- M8 sprint is the most active part of the codebase. Adding a required CI gate on an active sprint path risks blocking M8 PRs.
- Even if the eval exists but isn't in CI, that's a deliberate dev choice during a sprint — not necessarily a bug.

**Defend:**
- Eval datasets in PRs without CI registration become dead code. Real risk.
- M8 agent-service quality matters: CRM decision path is customer-facing.

**Verdict: WEAKENED**
Evidence insufficient. M8 timing wrong. Revisit post-M8 sprint when codebase settles.

---

## Summary

| Idea | Verdict |
|------|---------|
| Step 9L — nightly connector auth scan | SURVIVES → WINNER |
| os_tool_executions.py split issue | WEAKENED → defer to run 116 |
| CRM eval CI gate | WEAKENED → post-M8 |
| Gmail auth KB article | WEAKENED → parking lot (bonus with 9L) |
| Close stale subconscious PRs | WEAKENED → Step 9K handles escalation |
