# Run 65 Debate Log — 2026-06-23-pm

Top 3 debated: Idea 1 (plan-name guard), Idea 2 (CAN-SPAM), Idea 3 (kb-autopopulate).
Ideas 4 + 5 assigned to parking lot without full debate (no urgency escalation).

---

## Idea 1: Add plan-name guard Check 7 to check_project_invariants.py

### Round 1 — Challenge
**Against**: check_project_invariants.py already passes all 6 checks. Adding another may increase false positives if product intent is to have chatbot NOT in certain premium-only dicts (e.g., api_key_auth._ALLOWED_PLANS excludes chatbot intentionally — widget-only tier has no Zapier). A poorly scoped check creates noise, not signal.

**Defend**: The check guards the specific class that bit us: "plan exists in CURRENT_PAID_PLANS but has no AI token baseline in billing_reconciliation._PLAN_BASELINE_AI_TOKENS." This is the minimal invariant — every paid plan MUST have a token baseline, regardless of tier. The api_key_auth exclusion of chatbot is intentional and different. Scope the check narrowly: CURRENT_PAID_PLANS ⊆ _PLAN_BASELINE_AI_TOKENS. That's it.

**Verdict**: SURVIVES round 1. Scope concern valid but addressed by narrow guard on billing_reconciliation only.

### Round 2 — Challenge
**Against**: The implementation requires parsing Python source (frozenset literal + dict literal) inside a stdlib-only script. ast.literal_eval is fragile for multi-line dicts with comments. Risk of false negatives if regex parse fails silently.

**Defend**: check_project_invariants.py already uses regex parsing for other checks (column name patterns, widget byte-diff). Pattern is proven. Use `ast.parse()` on the source file and walk the AST for the assignment node — more robust than regex. If parse fails, FAIL the check explicitly (fail-open = correct behavior for a guard). No false negatives on parse failure.

**Verdict**: SURVIVES round 2. AST-walk approach is robust; fail-on-parse-error is the right default.

### Round 3 — Challenge
**Against**: Sequencing: the previous "Bonus B" note always said "after GH #292/#293 lands." Both are now implemented, so the sequencing block is cleared. But is there a risk the new check immediately fails on the current codebase (if any billing_reconciliation dict is still incomplete)?

**Defend**: The session-summary confirms all 3 services now correctly reference PREMIUM_PLANS or plan_catalog — chatbot has explicit token baseline in billing_reconciliation._PLAN_BASELINE_AI_TOKENS (800_000). agent_os has 5_000_000. Check 7 should PASS on the current codebase. Sequencing block cleared. Zero install risk.

**Verdict**: SURVIVES round 3. → **WINNER**

---

## Idea 2: CAN-SPAM physical address in cold-outreach body

### Round 1 — Challenge
**Against**: CAN-SPAM compliance is a real gap, but this is an Instantly.ai campaign configuration task — not a code change. The subconscious loop is designed for code improvements that can be recommended (and ideally autonomously implemented). Recommending "go into Instantly.ai and add your address" is operator-layer work that can't be AUTONOMOUS-EXECUTABLE and adds no code artifact to the repo.

**Defend**: The gap is real and has legal exposure. The subconscious has recommended operational improvements before (kb-autopopulate.sh, nightly SKILL.md changes). The email template could live in the repo (e.g., `docs/outreach-templates/`), making this code-adjacent.

**Verdict after round 1**: KILLED. The gap belongs in an operator checklist, not a subconscious recommendation that becomes a pending_approval item. Adding to pending without a code artifact is governance noise. Flag as operator task in backlog.

---

## Idea 3: Fix kb-autopopulate.sh (46+ days stale)

### Round 1 — Challenge
**Against**: 46 days of stale KB hasn't blocked any development work. The KB is a nice-to-have research layer, not load-bearing. The agent-browser CLI root cause is an environment issue (container doesn't have it installed). Even if we fix the script to use WebFetch instead, nightly cron in this remote execution environment may not persist CLI installs between runs.

**Defend**: 46 days means zero competitive intelligence, no CA AI law articles, no platform changelog articles. The KB is designed to prevent re-research — every missing article = research time burned again. Fixing the script to use WebFetch (native, always available) removes the environment dependency entirely. Real code change, not just "install the CLI."

**Round 2 — Challenge**: Even with the WebFetch switch, kb-autopopulate.sh runs a broad research sweep over 6+ topics. In a remote execution environment, scheduled cron may not run reliably. Spending M-effort on a script that may not execute is low ROI.

**Verdict after round 2**: SURVIVES WEAKENED → PARKING LOT. The fix is valid but lower priority than Check 7. Assign ROI 1.8 to parking lot. Run 66 candidate if no higher-urgency item emerges.

---

## Parking Lot (not debated)

- **Idea 4** (email_sequences.py split, 1143L): active_direction run 41, M-effort, human-required. No urgency escalation. Stays in parking lot.
- **Idea 5** (migration object-existence audit): valid S-effort autonomous candidate. No urgency escalation — GH #263 is false positive, not active bug. Parking lot.
- **CAN-SPAM**: operator task. Flagged in backlog as operator checklist item, not a subconscious code winner.

---

## Winner

**Idea 1: Add plan-name guard Check 7 to check_project_invariants.py**  
SURVIVES all 3 rounds. AUTONOMOUS-EXECUTABLE. No moratorium impact (pending_autonomous, not pending_approval). Sequencing block cleared today. Prevents the entire repricing-drift bug class.
