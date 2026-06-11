### Idea 3: Fix 10 Em-Dash Violations Batch — Restore check_project_invariants Exit 0

**Evidence:** `check_project_invariants.py` reports 10 em-dash violations in 7 files: `frontend/src/main.jsx:152`, `frontend/src/components/CookieConsent.jsx:5,31`, `frontend/src/components/MarketingUpsell.jsx:3`, `frontend/src/components/App.jsx:328`, `frontend/src/components/Sidebar.test.jsx:27,49`, `frontend/src/components/billing/ReferralCard.jsx:24,45`, `frontend/src/components/os/ComposerAttachments.jsx:1`. Introduced by a5c65b5 (8 violations) and 7c8825c (2 violations). Prior runs 49 (8db33df) and 54 (target violations cleared by a5c65b5 refactor) both addressed em-dash classes. 10 violations is the highest batch count in project history.

**Action:** Replace all 10 em-dash characters (—) with hyphens (-) in the affected files. Verify check_project_invariants exits 0 after applying Idea 1 as well.

**Impact:** Combined with Idea 1, restores check_project_invariants exit 0. Nightly SKILL.md Item A pre-condition met → Check 10 auto-wires tonight → future violations caught at commit. AUTONOMOUS-EXECUTABLE.

**Category:** code_health
