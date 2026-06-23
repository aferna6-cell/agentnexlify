# Run 65 Ideas — 2026-06-23-pm

## Evidence base
- Today's session (docs/dev-knowledge/session-summary-2026-06-23.md): both active moratorium_override bugs FULLY IMPLEMENTED
  - GH #292/#293: commits 57f2bb4d (plan-gating) + 29ed1d43 (reconciliation caps)
  - GH #308: commit 3a958e5f (delete_key in idempotency.py + stripe_webhooks.py callsite)
- Test suite: 2172 passing, 0 failing (post-implementation confirmed)
- Cold-outreach: 218 personal emails, 9 inboxes warming, launch target ~July 10
- git log 3d: session-summary + 3 implementation commits
- check_project_invariants.py: passes all 6 checks (includes widget sync, em-dash, schema field names, plan-naming)
- God-class candidates: email_sequences.py = 1143L (run 41 active_direction), Home.jsx = 1006L
- KB autopopulate: 46+ days stale (agent-browser CLI not installed)
- migration-triage-2026-06-22.md: GH #263 "24 pending migrations" largely false positive — need deterministic object-existence audit

## Candidate ideas

---

### Idea 1: Add plan-name guard Check 7 to check_project_invariants.py
**Category**: code_health  
**ROI**: HIGH  
**Effort**: S (~30 min)  
**AUTONOMOUS-EXECUTABLE**: YES  

GH #292/#293 took 7 days to find + 7 more to fix. Root cause: no automated guard catches when CURRENT_PAID_PLANS diverges from plan-specific dicts in services. The next repricing (or new plan addition) will cause the same class of bug unless a check exists.

Check 7: parse CURRENT_PAID_PLANS from plan_catalog.py, parse _PLAN_BASELINE_AI_TOKENS keys from billing_reconciliation.py, FAIL if any current paid plan is missing. Sequencing block ("after GH #292/#293") is now cleared — both bugs implemented today.

Since check_project_invariants.py already runs as pre-commit Check 13, any new check added to the script automatically becomes a pre-commit gate.

Pattern: same class as Check 11 (billing sentinel), Check 12 (timing-safe guard), Check 13 (invariant wire) — all implemented autonomously by nightly review.

**Status**: FROZEN = false. REJECTED = false.

---

### Idea 2: CAN-SPAM physical address in cold-outreach campaign body
**Category**: operational  
**ROI**: MEDIUM (legal compliance)  
**Effort**: S (~5 min)  
**AUTONOMOUS-EXECUTABLE**: NO  

Session summary flags: "CAN-SPAM gap: physical mailing address not yet in campaign body." 218 personal emails sent. CAN-SPAM requires physical postal address in commercial email. Gap exists in Instantly.ai campaign template.

Fix: add company physical address to Instantly.ai campaign body template. ~5 min operator task, no code change.

**Status**: FROZEN = false. REJECTED = false.

---

### Idea 3: Fix kb-autopopulate.sh (46+ days stale)
**Category**: operational  
**ROI**: MEDIUM  
**Effort**: M  
**AUTONOMOUS-EXECUTABLE**: PARTIAL  

KB autopopulate has been broken 46+ days — agent-browser CLI not installed in the environment. Knowledge base INDEX covers 110+ articles but has had zero new articles compiled since May. Competitive intelligence, CA AI companion law, platform changes — all missing.

Fix path: `which agent-browser` confirms absent → install via `npm install -g @anthropic-ai/agent-browser` (if available) OR replace agent-browser calls with native WebFetch in the autopopulate script.

**Status**: FROZEN = false. REJECTED = false.

---

### Idea 4: Split email_sequences.py god-class (1143L)
**Category**: code_health  
**ROI**: MEDIUM  
**Effort**: M (2h human)  
**AUTONOMOUS-EXECUTABLE**: NO  

Active_direction since run 41 (2026-05-30). 1143L, 3 clean concerns: CRUD / enrollment / processor. god-class-splitter SKILL.md ready. post-split-test-repair SKILL.md ready. No new evidence since run 41 — still valid but no urgency escalation.

**Status**: FROZEN = false. REJECTED = false.

---

### Idea 5: Create migration object-existence audit script
**Category**: code_health  
**ROI**: MEDIUM  
**Effort**: S (~45 min)  
**AUTONOMOUS-EXECUTABLE**: YES  

GH #263 "24 pending migrations" is a false positive (migration-triage-2026-06-22.md). Migrations 001–024 applied before tracking; naive number-diff reports 90 "pending." Problem: the pre-commit Check 5 (migration duplicate guard) doesn't catch this class. A deterministic object-existence audit script would query Supabase to verify each migration's tables/columns exist, replacing fragile number-diff. 

**Status**: FROZEN = false. REJECTED = false.
