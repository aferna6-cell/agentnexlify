# Ideas — Run 43 (2026-05-31-pm)

Evidence window: 3 days. Commits since run 42 (this morning): 1 (nightly-commit-review 2026-05-31, 0 fixes). Item A still not in pre-commit. email_sequences.py still 1255L. Moratorium day 29.

---

### Idea 1: Extend AUTONOMOUS-EXECUTABLE scope in nightly-commit-review SKILL.md to cover pre-commit bash additions
**Evidence:** Nightly 2026-05-31 (`2c15688`) ran at ~2:37 AM — 0 implementations. `grep check_project_invariants scripts/hooks/pre-commit` returns nothing — Item A unimplemented 29 days. `governance.json` has Item A as `pending_autonomous + autonomous_executable: true` (run 42 `00fc2af` applied). Current SKILL.md LOW-risk scope (line 65) covers SKILL.md creation but not bash hook additions. Run 42 winning concept Step 2 contains the patch; nightly didn't see a trigger that fires for it.
**Action:** Add bullet to `### LOW — Autonomous fix allowed` section of nightly-commit-review SKILL.md: "Bash additions to `scripts/hooks/pre-commit`" when `active_directions[].autonomous_executable: true` and winning-concept.md contains `AUTONOMOUS-EXECUTABLE`. Include Item A inline patch as the prototype. This is itself a SKILL.md edit — in autonomous scope per `d481799`.
**Impact:** Item A (28-day mandate, run 8) gets wired into pre-commit by tomorrow's nightly. Generalizes pattern: any future pre-commit hook labeled AUTONOMOUS-EXECUTABLE can execute the same way. Pending count -1 without human session.
**Category:** workflow

### Idea 2: Invoke /god-class-splitter on email_sequences.py
**Evidence:** 1255L confirmed today. Run 41 winner (2 days unimplemented). `/god-class-splitter` SKILL.md ready (`e848b87`). `/post-split-test-repair` SKILL.md ready (`d481799`). GH #112/#113: 1001 DB queries per 1000 enrollments — simpler post-split. 3 clean concerns: CRUD (lines ~1–400), enrollment (lines ~400–800), processor (lines ~800–1255).
**Action:** Human invokes `/god-class-splitter` on `backend/routers/email_sequences.py` → `email_crud.py` + `email_enrollment.py` + `email_processor.py`. Critical standing action: GH #181 fix first (~15 min).
**Impact:** Largest remaining router god-class cleared. Each module ~400L (under 600L threshold). Clears run 41 pending. Enables GH #112/#113 N+1 fixes. First production use of god-class-splitter skill.
**Category:** code_health

### Idea 3: AI-to-Human Handoff v1 — implement via Agent OS outbound
**Evidence:** Day 45 oldest pending (run 4, 2026-04-16). Critical gap all 7 industries. Agent OS PR #188 merged — `os_outbound_mirror.py` SMS/email delivery, 152 tests. Prior scope ~3 days (build plumbing); now ~1 day (routing + trigger detection only).
**Action:** widget_chat.py: detect handoff trigger phrases. Migration: `handoff_requests` table. Call `os_outbound_mirror.send_sms()` for owner notification. Lead status → `needs_follow_up`.
**Impact:** Critical gap closed. Differentiates on GoHighLevel at all plan tiers. Revenue unlock.
**Category:** customer_value

### Idea 4: Add Item D to AUTONOMOUS-EXECUTABLE after Item A confirms
**Evidence:** Item D (`lead-qualifier-eval.yml`) is purely additive new YAML — zero conflict risk. Once Item A confirms autonomous channel works for pre-commit additions, same pattern applies to new CI files. Moratorium sprint reduces to Item B only (widget sync guard, ~15 min).
**Action:** Run 44 recommendation: after Item A executes, add Item D directive to nightly SKILL.md AUTONOMOUS-EXECUTABLE block with inline YAML for `.github/workflows/lead-qualifier-eval.yml`.
**Impact:** Sprint reduces from 3 items to 1 (B only). Moratorium exit path: tonight Item A → run 44 Item D → human Item B → pending ≤ 2 = exit.
**Category:** operational

### Idea 5: GH #107 Zapier API key plan_status enforcement
**Evidence:** GH #107 open 31 days (2026-04-30). `zapier_auth.py::_get_api_key_client` resolves keys without `plan_status` check. Cancelled tenants bypass tier gate. Parking lot ROI 2.5. Agent OS outbound now live — Zapier bypass could trigger unauthorized automation.
**Action:** Add `AND plan_status IN ('active', 'trialing')` filter to `_get_api_key_client`. Add regression test. Route via issue-to-pr-loop.
**Impact:** Security: closes tier-bypass vector. ROI 2.5 (highest remaining security item). Independent of moratorium.
**Category:** code_health / security
