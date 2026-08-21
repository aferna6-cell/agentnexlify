# Ideas — Run 2026-08-21

## Evidence Digest

- Nightly-2026-08-21: 2 commits reviewed (clean), 0 issues filed, 0 bug fixes. Step 9J NOT in SKILL.md (grep: 0). 1st carry-forward — autonomous-executable condition met per governance mandate.
- Step 9I first execution (nightly-2026-08-20): swept 97/97 backend routers — ALL missing Depends(block_demo_role). GH #669 filed. Demo tenants can call every mutation endpoint.
- GH #399 (AUTOPILOT_GH_TOKEN): Day 40+, 30 ai-ready issues blocked. GH #403 (KB autopopulate): 28+ days stale, GH Actions secrets still unset.
- 6 Dependabot PRs aging (#629/#630/#631/#649/#665/#666) — 4 consecutive morning digests called them safe to merge with zero action.
- No production code commits in last 3 days (only nightly log + subconscious run 108 artifacts).

---

### Idea 1: Implement Step 9J directly (AUTONOMOUS-EXECUTABLE — 1st carry-forward mandate)
**Evidence:** Run 108 winner. Nightly-2026-08-21 confirms NOT in SKILL.md (grep: 0 occurrences). Governance mandate states "autonomous-executable if not approved by run 109 (1st carry-forward)". Same channel: Steps 9C/9E/9F/9G/9I all implemented via same SKILL.md edit within 1-2 cycles. Exact block documented in subconscious/runs/2026-08-20/winning-concept.md. 6 Dependabot PRs currently aging; 4 morning digests all flagged them safe.
**Action:** Add Step 9J block to .claude/skills/nightly-commit-review/SKILL.md after Step 9I block (exact content from run 108 winning-concept.md). Block: list open Dependabot PRs → check mergeable_state==clean + no review requests + no blocking labels → squash-merge eligible PRs → log count.
**Impact:** Dependabot PRs auto-merged within 24h of CI green, permanently. Security patches on 24h cadence vs current 2-4 week delays. ~15 min/week manual merge overhead eliminated.
**Category:** operational

---

### Idea 2: Step 9K — Add stale subconscious PR closer to nightly SKILL.md
**Evidence:** Run 108 parking lot named Step 9K as run 109 candidate. Nightly-2026-08-20 noted 5 draft PRs open (subconscious runs pile). With run 105 establishing git push + PR creation, each run adds a PR that never merges unless human closes. PR board noise hides real review needs.
**Action:** Add Step 9K block after Step 9J in nightly SKILL.md: list open PRs with head branch starting "subconscious"; if PR age >30 days AND no review activity (0 approved reviews, 0 human comments), close it with message "superseded by run N artifacts — see subconscious/runs/2026-08-21/ for current direction".
**Impact:** PR board stays clean. Human sees only recent subconscious direction, not 10+ stale draft PRs. Prevents confusion about which direction is current.
**Category:** operational

---

### Idea 3: Post middleware-level fix proposal comment on GH #669
**Evidence:** Step 9I found 97/97 routers missing block_demo_role. Per-endpoint patching requires 97+ file changes — not viable via nightly autonomous channel. Middleware fix (FastAPI `app.add_middleware(DemoRoleBlockMiddleware)`) would protect all existing AND future endpoints in one change. Without framing this choice, human may attempt per-router fix, creating O(n) work every time a new router is added.
**Action:** Post comment on GH #669 proposing middleware-level FastAPI solution with implementation sketch: `DemoRoleBlockMiddleware` checks request.method in POST/PUT/DELETE/PATCH, reads JWT role claim, returns 403 if role=demo. Skiplist for public/webhook/auth routes. Contrast with per-endpoint approach (97 files now, drift forever).
**Impact:** Frames the architectural decision. Prevents 97-file PR that misses the root cause. Human can approve middleware approach and close the class in one PR.
**Category:** code_health

---

### Idea 4: Add block_demo_role class bug pattern to bug-patterns.md
**Evidence:** GH #669 (97/97 routers). Bug-patterns.md documents "Zapier API key without plan_status" and "booking CTA plain text" — same documentation pattern. The block_demo_role class is now confirmed via automated sweep. Future sessions writing new routers won't know this is a class problem without bug-patterns.md entry.
**Action:** Append entry to docs/dev-knowledge/bug-patterns.md: document the class pattern ("new router endpoints added without block_demo_role Depends()"), root cause (no structural enforcement — only per-endpoint convention), and prevention note (add Depends(block_demo_role) to every POST/PUT/DELETE/PATCH route, OR use middleware-level enforcement).
**Impact:** Prevents future rediscovery. Future Claude sessions writing new routers will read this and add the guard. Karpathy principle: document the class, not the instance.
**Category:** code_health

---

### Idea 5: GH #403 targeted diagnostic — enumerate ALL missing secrets
**Evidence:** Run 107 posted ANTHROPIC_API_KEY setup steps. Run 108 bonus posted SUPABASE_URL + SUPABASE_ANON_KEY diagnostic. 28+ days stale, no human action after 2 targeted comments. Root cause may be third secret missing (SUPABASE_SERVICE_ROLE_KEY or GITHUB_TOKEN). KB autopopulate.yml script needs inspection.
**Action:** Read .github/workflows/kb-autopopulate.yml to enumerate every env var consumed by the workflow; cross-reference ops/credential-rotation-schedule.md; post a final definitive comment on GH #403 listing EVERY secret required with exact Railway→GitHub secret transfer steps. Mark as "last diagnostic — human must action."
**Impact:** If a third secret is the blocker, unblocks 28-day KB staleness in one human action. If all secrets were already set and the script itself is broken, reveals that and shifts the investigation.
**Category:** operational
