# Ideas — Run 2026-08-20-pm (Run 109)

## Evidence Basis

**Mandate check (run_109_mandate):**
1. Step 9J ABSENT from SKILL.md (grep returns 0) — 1st carry-forward → AUTONOMOUS-EXECUTABLE
2. Step 9I first execution (nightly-2026-08-20): 97/97 checked routers missing block_demo_role → GH #669 filed (class-wide, middleware-level fix recommended)
3. GH #403 bonus comment from run 107: no human action in 48h+, KB still 28d stale
4. GH #399: OPEN Day 40+, autopilot loop still blocked
5. Stale subconscious PRs: #575 (27d), #613 (19d), #626 (17d), #648 (9d), #653 (8d) — 5 open → Step 9K condition MET (≥3)

**New signals:**
- 6 Dependabot PRs still aging (#629/#630/#631/#649/#665/#666)
- Step 9I sweep confirms nightly sweep channel working (filed GH #669 correctly)
- Morning digest continues flagging Dependabot PRs as "low risk, merge" with zero action taken

---

### Idea 1: Step 9J — Dependabot Auto-Merge in nightly SKILL.md (1st carry-forward, AUTONOMOUS-EXECUTABLE)
**Evidence:** run_108_mandate explicitly named Step 9J. 6 Dependabot PRs aging 2-16d. Morning digests 2026-08-11/12/17/18 all flagged same PRs as safe. run_109_mandate item 6: Step 9K is candidate IF subconscious PR count ≥3, but Step 9J is the PRIMARY mandate item (item 1 = verify Step 9J present). Escalation condition in governance: "Autonomous-executable if not approved by run 109 (1st carry-forward mandate)". This is run 109.
**Action:** Add Step 9J block to .claude/skills/nightly-commit-review/SKILL.md after Step 9I (before step 10). Block: list open Dependabot PRs via mcp__github__list_pull_requests, check mergeable_state==clean + no review requests + no blocking labels, merge eligible via squash, log count.
**Impact:** Security patches applied within 24h of CI green, indefinitely. 15 min/week manual merge overhead eliminated. 6 PRs currently aging resolved.
**Category:** operational

### Idea 2: Step 9K — Stale Subconscious PR Commenter in nightly SKILL.md
**Evidence:** run_109_mandate explicitly names Step 9K as candidate if PR count ≥3 (MET: 5 open). #575 (27d), #613 (19d), #626 (17d) have been sitting for weeks. Morning digest shows #613 as "superseded by #653". PR noise makes human review harder.
**Action:** Add Step 9K block to SKILL.md after Step 9J. Block: list open PRs with head branch matching "subconscious/*", for each >21d old: check if a newer subconscious run exists covering same direction, post comment noting possible supersession, label with "stale". Do NOT auto-close — human decides to close.
**Impact:** Reduces PR noise. Flags superseded PRs without destructive auto-close.
**Category:** operational

### Idea 3: Post GH #669 middleware implementation sketch
**Evidence:** Step 9I first execution filed GH #669 (95 routers, class-wide gap). Middleware approach recommended in nightly log. No implementation design exists yet. Per-file patching is impractical (95 files). Human engineer needs a concrete sketch to act on.
**Action:** Post detailed FastAPI middleware implementation sketch as comment on GH #669 — middleware class that intercepts POST/PUT/DELETE/PATCH requests, checks for demo role, raises 403, with explicit exclusions list.
**Impact:** Unblocks human implementation of class-wide security fix. Reduces the 95-file problem to a 1-file solution.
**Category:** code_health (security)

### Idea 4: Comment on GH #403 with all 3 required secrets (SUPABASE_URL + SUPABASE_ANON_KEY diagnostic)
**Evidence:** KB 28d stale. Run 107 posted ANTHROPIC_API_KEY comment with 5-step setup path. No human action in 48h+. Run 108 winning-concept.md flagged as bonus: SUPABASE_URL + SUPABASE_ANON_KEY may be second blocker. New diagnostic angle not yet posted.
**Action:** Post comment on GH #403 listing all 3 required secrets (ANTHROPIC_API_KEY + SUPABASE_URL + SUPABASE_ANON_KEY) with where to find each value and exact steps to add each to GH Actions.
**Impact:** May unblock KB autopopulate. Diagnoses if ANTHROPIC_API_KEY was added but second blocker exists.
**Category:** operational

### Idea 5: Merge PR #653 (contains run 102-107 subconscious artifacts)
**Evidence:** PR #653 draft 8d. Contains route-security-guard-audit SKILL.md, git push Phase 8 fix, Step 9I docs. Step 9I now live in code separately (dccd591). #653 still needs merge to close SKILL.md tracking loop and reduce open PR count.
**Action:** Review and merge PR #653 (or request merge via comment). Draft PR, low risk — all code already shipping in main.
**Impact:** Closes tracking loop. Reduces stale PR count by 1. Adds route-security-guard-audit SKILL.md to main.
**Category:** workflow
