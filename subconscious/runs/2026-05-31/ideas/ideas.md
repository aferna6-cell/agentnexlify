# Ideas — Run 42 (2026-05-31)

## Evidence Digest (200 words max)

Nightly 2026-05-31 reviewed 3 commits, applied 0 fixes — all LOW-risk docs/skills. Moratorium day 28. All Items A/B/D still MISSING (confirmed: grep 0 for check_project_invariants in pre-commit; check-widget-sync.sh absent; lead-qualifier-eval.yml absent). email_sequences.py confirmed 1255L — run 41 winner, day 1 unimplemented. GH #181 still open — 15000/25000 absent from billing.py. Phase-C cleanup landed (5 commits: removed 20+ stale files, audits, plans, buddy skill). Agent OS rehaul fully merged (301cbcf, 152 tests, SMS/email/FB outbound). 62 commits last 7 days but majority are organizational (phase-c) or ops/subconscious. customer-gaps.md: AI-to-Human Handoff Critical; Custom Automation Templates Open/Medium. Key new insight: billing-constant-guard Check 11 (22-line bash) was autonomously implemented by 061582c — exact same risk class as Item A (3-line pre-commit addition) which has sat frozen as "subsumed_in_sprint" for 28 days. The grouping label is the blocker, not the risk.

---

### Idea 1: De-couple Item A from Sprint — Mark check_project_invariants Pre-commit as Standalone AUTONOMOUS-EXECUTABLE

**Evidence:**
- Check 11 (22-line bash, 061582c) was autonomously implemented by nightly review — direct to main, no sprint PR needed
- Item A is 3 lines of bash (calls check_project_invariants.py in pre-commit) — lower complexity than Check 11
- Item A has been "subsumed_in_sprint" for 28 days; the sprint has never been invoked
- Run 26 killed "Items A+B concurrent" due to sprint PR conflict — Item A solo has no such conflict (direct main commit)
- Nightly review standing actions already mention Item A — only the "subsumed_in_sprint" label prevents action
- The autonomous channel is now repaired for both code additions (061582c) and SKILL.md creation (d481799)

**Action:** Update governance.json Item A status from "subsumed_in_sprint" to "pending_autonomous". Add explicit AUTONOMOUS-EXECUTABLE directive to nightly-commit-review SKILL.md standing actions section for Item A. Include 3-line pre-commit patch inline so nightly review can execute without lookup.

**Impact:** One pending item resolved autonomously, moratorium pending count decreases by 1. Proves autonomous channel works on pre-commit bash — unlocks same pattern for Item D (CI workflow YAML, additive file).

**Category:** workflow

---

### Idea 2: Invoke /moratorium-sprint

**Evidence:**
- Day 28 moratorium. Items A/B/D all MISSING.
- moratorium-sprint SKILL.md ready (7985fbb, 2026-05-19)
- 3 items: A (~5 min), B (~15 min), D (~20 min) → ~40 min total
- After sprint: pending ≤ 2 → moratorium exits
- Human present in interactive session

**Action:** Type `/moratorium-sprint` in this interactive session and execute the 3-item sequence.

**Impact:** Pending -3, moratorium exits. Highest total impact of any single action.

**Category:** workflow

---

### Idea 3: Post-Phase-C Architecture Audit

**Evidence:**
- Phase-C cleanup: 5 commits removed 20+ stale files, audits, plans, buddy skill (5e27a13, b5fc713, 80dc695, 1207f1b, f519a5f)
- Last architecture audit was 2026-04-18 (43 days ago)
- Agent OS rehaul (301cbcf) added significant production code post-audit
- god-class-refactor_plan.md has 54 targets but was written pre-phase-C and pre-Agent-OS

**Action:** Invoke /improve-architecture to generate fresh audit; output audits/audit-architecture-2026-05-31.md.

**Impact:** Identifies top god-class targets post-phase-C; re-prioritizes the 54-target split plan; may surface dead code newly orphaned by phase-C removal.

**Category:** code_health

---

### Idea 4: Write Custom Automation Templates v1 Spec

**Evidence:**
- customer-gaps.md: "Custom automation templates" — Open Cross-Industry, Medium effort
- Infrastructure exists (email_sequences.py, birthday automation migration 129, post-service follow-up patterns)
- After email_sequences split (run 41 winner), enrollment module becomes the natural home for template logic
- No existing spec file for this feature; daily-skills.md gate mandates spec before any planning

**Action:** Create specs/custom-automation-templates_spec.md — goals, non-goals, user stories, acceptance criteria for tenant-configurable trigger/action templates.

**Impact:** Unblocks next customer value sprint post-moratorium; defines the next M-effort feature after AI-to-Human Handoff.

**Category:** customer_value

---

### Idea 5: Zapier API key plan_status Enforcement (GH #107 — Security)

**Evidence:**
- GH #107 open 45+ days. Parking lot ROI 2.5, note: "promote to first non-moratorium winner if #107 still open"
- backend/services/zapier_auth.py::_get_api_key_client resolves keys without plan_status check
- Cancelled tenants with un-revoked keys bypass tier gate — revenue leakage + security gap
- Phase-C cleanup shows codebase is being audited; security fix has natural momentum
- First non-moratorium candidate if moratorium exits

**Action:** Add plan_status IN ('active','trialing') filter to _get_api_key_client; add regression test; close GH #107.

**Impact:** Closes security gap for cancelled tenants. ROI 2.5. Prevents revenue leakage without user-visible changes.

**Category:** code_health / security
