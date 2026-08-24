# Improvement Backlog — 2026-08-23 (Run 109)

## Executed This Run

| Idea | Action | Status |
|------|--------|--------|
| Step 9J — Dependabot Auto-Merge | Inserted into nightly SKILL.md (autonomous-executable, 1st carry-forward) | DONE |

---

## Active Parking Lot (Run 110+ Candidates)

### Step 9K — Stale Autonomy PR Closer
- **What:** Nightly step to close PRs older than 14 days with "subconscious" in branch name, with explanatory comment
- **Evidence:** 4+ draft subconscious PRs aging (#606/#611/#613/#625). governance.json run_109_mandate named it as candidate if PR count ≥3 (met)
- **Blocker:** No mandate. Pattern (auto-closing PRs) needs human approval before nightly skill inclusion
- **Next step:** Propose in run 110. Wait for explicit human approval before inserting into SKILL.md
- **Priority:** Medium

### Middleware-Level block_demo_role FastAPI Guard
- **What:** FastAPI middleware in main.py to intercept POST/PUT/DELETE/PATCH from demo-role tenants; closes GH #669 with one change instead of 97 router patches
- **Evidence:** GH #669 (97/97 routers missing Depends(block_demo_role), filed 2026-08-20)
- **Blocker:** Human-approval required. Auth-layer change. Touches main.py (god class). Needs grill-me + compound-engineering pipeline. Exempt logic for webhooks/admin needed.
- **Next step:** File as GH issue tagged "architecture-proposal" linking to GH #669 for human decision
- **Priority:** High (security impact) but not autonomous-executable

---

## Persistent Open Blockers (Requiring Human Action)

| Issue | Age | Description | Last Action |
|-------|-----|-------------|-------------|
| GH #399 | Day 44+ | AUTOPILOT_GH_TOKEN expired — 30 ai-ready issues blocked | 4+ escalation comments; last 2026-07-16 |
| GH #403 | 31d stale | ANTHROPIC_API_KEY missing in GH Actions — KB autopopulate dark | 2 targeted comments runs 107+108; no action |
| GH #669 | Filed 2026-08-20 | 97/97 routers missing Depends(block_demo_role) | Awaiting fix via issue-to-pr-loop |

---

## Killed Ideas (Do Not Repropose)

| Idea | Reason |
|------|--------|
| KB Local Fallback Path | Uncertain whether ANTHROPIC_API_KEY available in nightly container; complex partial-compile risk |
| GH #399 Cost-Calculation Comment | 4+ prior escalations with zero effect; structural blocker not addressable by framing changes |
| ai_human_handoff | Frozen since early runs — NEVER repropose |

---

## Nightly SKILL.md Step Inventory (as of run 109)

| Step | Name | Added Run |
|------|------|-----------|
| 9C | Auto-bug-fix commit | ~run 95 |
| 9E | GH issue filing for MEDIUM/HIGH bugs | ~run 97 |
| 9F | Bonus loop — morning/evening logs | run 99 |
| 9G | KB autopopulate trigger | run 101 |
| 9I | Route security guard sweep | run 107 |
| **9J** | **Dependabot auto-merge** | **run 109 (this run)** |
