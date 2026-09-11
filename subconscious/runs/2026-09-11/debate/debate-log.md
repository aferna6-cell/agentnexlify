# Debate Log — Run 119 (2026-09-11)

## Candidates Selected for Debate
1. **Idea 1**: Step 9E Credential Escalation — auto-file GH issue when token within 10d of threshold
2. **Idea 2**: Step 9G MCP Fix — replace broken gh CLI with mcp__github__actions_run_trigger
3. **Idea 3**: Governance.json Meta-Fix — add verified_implemented status, fix Step 9L stale flag

Ideas 4 and 5 dropped from debate: Idea 4 (os_tool_executions.py Step 9M) is ready but lower urgency than 1-3. Idea 5 (stalled issues nudge) is additive but security urgency is already tracked by #669/#660.

---

## Round 1: Initial Claims

**Idea 1** claims: AUTOPILOT_GH_TOKEN expires in 7 days. If it expires, the autonomous engineering loop dies silently. Step 9E detects the risk but files no actionable GH issue. Auto-filing turns a log warning into a trackable human-action item.

**Idea 2** claims: Step 9G has been broken for 4+ consecutive nightly runs. KB is 16 days stale. The fix is a 5-line SKILL.md change: swap `gh workflow run` for `mcp__github__actions_run_trigger`. Concrete, additive, autonomous-executable.

**Idea 3** claims: Governance.json stale flags caused 3 wasted carry-forward rounds on Step 9L. Adding `verified_implemented` status prevents future false carry-forwards. Compounding meta-benefit.

---

## Round 2: Hard Objections

### Objection to Idea 1
**Challenge**: AUTOPILOT_GH_TOKEN is listed at 69 days (threshold 76d). The nightly already posted a warning. Is an additional GH issue actually necessary, or does the human already know?

**Defense**: The warning is in `docs/dev-knowledge/nightly-reviews/2026-09-11.md` — a file the human reads when checking logs. The issue-to-PR loop, Slack notifications, and GH Issues are the reliable attention channels. Warnings in log files are low-priority in practice. Three consecutive nightlies flagged this (Sep 9, 10, 11); zero human action. A GH issue with `human-action-required` label creates a notification + appears in the open issues list. Dedup guard ensures only one is filed.

**Weakness**: If AUTOPILOT_GH_TOKEN is rotated manually before the nightly next runs, the GH issue becomes stale clutter. Mitigation: add note "Close this issue once rotation complete."

**Objection PARTIALLY SUSTAINED**: Good idea, but the urgent value is THIS token expiring in 7 days, not the general pattern. The SKILL.md edit is valuable; the specific token is a one-time problem.

---

### Objection to Idea 2
**Challenge**: GH Actions are "dark since 2026-07-20" per CLAUDE.md (GH #500). If workflows are disabled, mcp__github__actions_run_trigger will also fail (API call to a disabled workflow). Is this fix actually viable?

**Defense**: "Dark" means no SCHEDULED crons — not workflows disabled entirely. The nightly review itself says: "Manual trigger: bash scripts/daily/kb-autopopulate.sh or trigger via GH Actions UI." If the GH Actions UI can trigger it manually, the API can too. mcp__github__actions_run_trigger sends a `workflow_dispatch` event, same as UI manual trigger. This should work.

**Counter-challenge**: Need to verify `kb-autopopulate.yml` has `workflow_dispatch:` in its triggers. If the workflow only has `schedule:` trigger, manual dispatch won't work.

**Defense**: This is verifiable. If `workflow_dispatch:` is missing from kb-autopopulate.yml, the SKILL.md edit should add that note as a prerequisite. But 4+ consecutive broken nights with KB at 16 days stale — this is the fix with highest remediation value.

**Weakness**: Cannot verify workflow_dispatch availability without reading kb-autopopulate.yml. Adds a dependency.

**Objection SUSTAINED as conditional**: Strong fix, but requires verifying workflow_dispatch in kb-autopopulate.yml. If missing, the fix is still wrong. Need pre-verification in the winning-concept.

---

### Objection to Idea 3
**Challenge**: Governance.json is a subconscious-internal file. This meta-fix only improves the subconscious loop efficiency — no user-visible benefit. Is this the right use of one run?

**Defense**: The stale flag caused 3 consecutive wasted runs (115-117) on Step 9L. If governance.json stays corrupted, future runs repeat the same error. The `verified_implemented` vs `implemented` distinction is foundational for the loop's integrity. This is debt that compounds.

**Counter-challenge**: Run 118 already identified and documented the stale flag issue. The correct fix was immediate JSON edit in run 118. This is a repeat recommendation. Why wasn't it done then?

**Defense**: Run 118 winner was Step 9J cursor (which turned out moot). The governance.json fix was identified but not actioned as the primary winner. This run can action it.

**Weakness**: Lowest user-visible impact of the three candidates. Also — the JSON edit itself is trivial (one field change). Elevating it to "winning concept" status may be disproportionate to its impact.

**Objection SUSTAINED**: Correct thing to do, but should be a bonus action — not the primary winner.

---

## Round 3: Impact Comparison

| Idea | Urgency | Impact | Risk | Effort |
|------|---------|--------|------|--------|
| 1: Step 9E credential escalation | HIGH (7d) | HIGH (prevents loop death) | LOW | S (SKILL.md + JSON) |
| 2: Step 9G MCP fix | MEDIUM (ongoing) | HIGH (fixes recurring failure + KB freshness) | LOW-MEDIUM (workflow_dispatch dependency) | S (SKILL.md) |
| 3: Governance meta-fix | LOW | MEDIUM (loop integrity) | NONE | XS (JSON edit) |

---

## Round 4: Final Verdict

**Idea 1 WINS** on urgency and impact.

AUTOPILOT_GH_TOKEN expires in 7 days. The autonomous engineering loop — the mechanism that runs this very subconscious — depends on that token. Step 9E detects the risk but fires no escalation. Adding auto-GH-issue-filing when any credential enters the 10-day danger window:
1. Creates a trackable human-action item (GH issue with deadline)
2. Is dedup-guarded (no spam across nightly runs)
3. Applies to all credentials going forward, not just AUTOPILOT_GH_TOKEN
4. Is autonomous-executable via SKILL.md edit

**Idea 2 BONUS** (should be implemented alongside winner): Governance.json correction for Step 9L and the step9j-cursor.json initial file creation (bonus actions that don't require human approval).

**Idea 3 BONUS** (trivial JSON edit, bundle with winner commit).

---

## Decision

**WINNER: Idea 1 — Step 9E Credential Escalation via GH Issue Auto-Filing**

Rationale: highest-urgency finding (7 days to expiry), highest structural value (applies to all credentials permanently), autonomous-executable (SKILL.md edit = proven channel), prevents the single most catastrophic failure mode (autonomous loop death due to expired credentials).
