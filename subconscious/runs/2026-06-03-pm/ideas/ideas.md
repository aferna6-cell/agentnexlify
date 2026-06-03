# Ideas — Run 49 (2026-06-03-pm)

## Evidence Summary

**What changed:** Item D implemented autonomously (nightly 42992fa) — lead-qualifier-eval.yml created after 48-day pending. Zero production code commits since 2026-06-01 (nightly em-dash comment fix). All 5 JSX em-dash violations persist: IntegrationsPage:1018, SettingsInboundChannels:220-221, MessagingSettingsCards:263/276. Nightly June 3 log explicitly noted violations but logged them as "Fix: replace em dashes — recommendation to human", not as autonomous action. Widget sync guard (check-widget-sync.sh) MISSING. Check 10 still not in pre-commit.

**Key finding:** Nightly ran 3 times since violations were identified (June 1, 2, 3) WITHOUT auto-fixing JSX content em-dashes. Reason: SKILL.md autonomous scope covers pre-commit bash additions (run 43) and CI YAML (run 47) but NOT JSX content string fixes. e7e0a3b (June 1) fixed em-dashes in comments — different scope than UI copy strings. The scope gap is the blocker.

**Run 48 winner status:** NOT implemented (Items A+B). Same recommendation 2 consecutive runs. Mechanism change required.

---

### Idea 1: Extend nightly SKILL.md scope + apply 5 em-dash patches (AUTONOMOUS-EXECUTABLE)
**Evidence:** Nightly ran 3x without fixing JSX content em-dashes — scope gap confirmed by June 3 log. SKILL.md scope extension is the proven mechanism: runs 40 (SKILL.md creation), 43 (pre-commit bash scope), 47 (CI YAML scope) all implemented autonomously after scope extension. e7e0a3b confirmed nightly CAN fix em-dashes in source files. 5 exact violations known with file:line precision. After fix: check_project_invariants.py exits 0 → nightly auto-wires Check 10.
**Action:** Add "JSX/JS em-dash → hyphen replacement when check_project_invariants.py fails em-dash check" to LOW-risk autonomous scope in nightly-commit-review SKILL.md. Provide 5 inline patches in winning-concept.md as AUTONOMOUS-EXECUTABLE directive. Nightly applies scope extension + patches in same commit.
**Impact:** Tonight fixes em-dashes → check_project_invariants exits 0 → tomorrow night auto-wires Check 10 (Item A). 2-night cascade closes 1 moratorium item without human action. Breaks 2-run human-execute stall via mechanism change.
**Category:** workflow

---

### Idea 2: Items A+B combined — human-execute (same as run 48 winner)
**Evidence:** Run 48 winner, NOT implemented. 5 em-dash violations known exactly. Widget sync guard script known exactly (full bash in run 48 winning-concept.md). Combined ~25 min. Moratorium day 34.
**Action:** Fix 5 em-dash lines + create scripts/check-widget-sync.sh + wire pre-push + fix CLAUDE.md Invariant #4. Implementation sketch identical to run 48 winning-concept.md §Steps 1-4.
**Impact:** 2 moratorium items closed (Items A+B). check_project_invariants exits 0. Widget copies protected. Moratorium 2 closures closer to exit.
**Category:** code_health / workflow

---

### Idea 3: email_sequences.py god-class split
**Evidence:** 1255L, day 7 unimplemented (run 41 active_direction). Both skills ready: god-class-splitter (e848b87) + post-split-test-repair (d481799). GH #112/#113 N+1 queries open. GH #181 billing fix is prerequisite (AMOUNT_TO_PLAN path confirmed: backend/routers/billing.py:263, ~15 min). Moratorium active but MEDIUM-effort item — blocked by prerequisite, not moratorium per se.
**Action:** First fix GH #181 (~15 min), then invoke /god-class-splitter on email_sequences.py → split into email_crud + email_enrollment + email_processor.
**Impact:** 1255L → 3 modules <500L. RULE 9 compliance. GH #112/#113 N+1 easier post-split. Closes run 41 active_direction.
**Category:** code_health

---

### Idea 4: Zapier API key plan_status enforcement (GH #107)
**Evidence:** GH #107 open 35+ days. backend/services/zapier_auth.py::_get_api_key_client resolves keys without plan_status check. Cancelled tenants with un-revoked keys bypass tier gate. ROI 2.5 (highest in parking_lot). S-effort (~15 min). Previously killed in debates only due to "moratorium + wrong queue" — not due to technical objection.
**Action:** Add `plan_status IN ('active', 'trialing')` filter to _get_api_key_client query in zapier_auth.py + regression test. Close GH #107.
**Impact:** Cancelled tenants cannot use Zapier integration. Revenue protection + tier enforcement hardened.
**Category:** code_health (security)

---

### Idea 5: AI-to-Human Handoff minimal v1
**Evidence:** Run 4 winner, 48 days oldest pending. Critical gap all 7 industries. os_outbound_mirror.py (PR #188, merged 2026-05-27) handles SMS/email/FB delivery with 152 tests. Scope from ~3 days → ~1 day. 7+ prior recommendations without implementation.
**Action:** Add explicit trigger detection to widget_chat.py, call os_outbound_mirror to notify owner, update lead status to 'needs_follow_up'.
**Impact:** Closes oldest Critical customer gap. Differentiator vs GoHighLevel. Every vertical needs this.
**Category:** customer_value
