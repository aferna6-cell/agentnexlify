# Run 105 — Candidate Ideas (2026-08-15-pm)

## Context
Run 104 winner status: PARTIAL — SUPABASE_ACCESS_TOKEN row pre-existed in credential schedule
(added in run 84 era), "Action Required" note block not added, Step 9E still flags "unknown state" noise.
route-security-guard-audit SKILL.md: 3rd carry-forward — escalation threshold met.
No production code commits 3+ days. GH #399 open Day 37+.

---

### Idea 1: Write route-security-guard-audit SKILL.md directly (3rd carry-forward escalation)

**Evidence:**
- Run 102 winner (2026-08-11-pm), carried forward runs 103 + 104 = 3 consecutive cycles without implementation
- Per subconscious precedents: Step 9F escalated at run 99 (3rd cycle), Step 9G escalated at run 101 (6th cycle)
- scoring_config.py (grep confirmed): missing block_demo_role on all 4 mutating routes
- appointment_briefs.py: GH #643 open 8 days, draft PR #653 not merged — same class of gap
- SKILL.md content already written in `subconscious/runs/2026-08-11-pm/winning-concept.md`
- skill-discovery-2026-08-10 explicitly proposed this skill

**Action:** Write `.claude/skills/route-security-guard-audit/SKILL.md` using content from run 102 winning-concept.md.
Zero edits required — content is final and tested.

**Impact:** Systematic detection prevents future block_demo_role gaps from hiding in new routers.
Every future payment/scoring/AI endpoint gets a repeatable 6-step audit. Compounding benefit per route added.

**Category:** code_health
**Effort:** XS (content ready — write one file, ~5 min)

---

### Idea 2: Fix Step 9E to handle 'unknown' last_rotated gracefully

**Evidence:**
- nightly-2026-08-15 Step 9E: "SUPABASE_ACCESS_TOKEN: unknown state (not yet set in rotation schedule) — flag"
- ops/credential-rotation-schedule.md: SUPABASE_ACCESS_TOKEN row EXISTS with `last_rotated = unknown`
- Step 9E's parser treats "unknown" same as "row missing" → generates misleading output
- This fires every nightly indefinitely until the human fills in a real date
- Run 104 winner added the note context but did NOT fix the parser
- Pattern: same class as Step 9C fix (run 103) which added age-gate logic alongside consecutive-failures check

**Action:** Edit Step 9E in `.claude/skills/nightly-commit-review/SKILL.md`: when row exists but last_rotated
is "unknown" or "unknown — not yet set in environment", output `NEEDS_DATE` instead of `not yet set in schedule`.
Log: "SUPABASE_ACCESS_TOKEN: date untracked — check ops/credential-rotation-schedule.md Notes section".

**Impact:** Eliminates misleading Step 9E output. "NEEDS_DATE" is actionable (human knows what to do).
"not in schedule" is confusing (row IS in schedule). One SKILL.md line change.

**Category:** workflow
**Effort:** XS (~10 min)

---

### Idea 3: Open GH issue for scoring_config.py block_demo_role (ai-ready security)

**Evidence:**
- Direct grep: scoring_config.py imports only `require_role`, no `block_demo_role`, no `ai_usage_guard`
- 4 mutating routes: POST /scoring (seed), PUT /scoring/{id}, DELETE /scoring/{id}, DELETE /scoring
- Same class as GH #643 (appointment_briefs.py) — confirmed security gap
- No GH issue opened after run 104 surfaced this finding
- Route-security-guard-audit SKILL.md (idea 1 winner) would detect this systematically in future
- With ai-ready label: issue-to-pr-loop can pick up once GH #399 resolved

**Action:** File GH issue titled "fix(security): scoring_config.py missing block_demo_role on mutating routes"
with labels `security`, `ai-ready`, `block_demo_role`. Body: reference GH #643, note 4 routes, implementation
sketch: add `from backend.dependencies import block_demo_role` + `dependencies=[Depends(block_demo_role)]` on
POST/PUT/DELETE endpoints.

**Impact:** Closes confirmed security gap. Demo tenants can currently create, update, delete scoring factors.
Queued for autopilot loop when GH #399 resolved.

**Category:** code_health/security
**Effort:** XS (~5 min via GH MCP)

---

### Idea 4: Add SUPABASE_ACCESS_TOKEN "Action Required" note block (carry-forward from run 104)

**Evidence:**
- Run 104 winning-concept.md proposed a detailed note block for ops/credential-rotation-schedule.md
- Current file has no "Action Required" note — only a generic bullet in ## Notes
- Human visiting GH #394 (brain connector 23d stale) has no clear checklist for SUPABASE_ACCESS_TOKEN
- Step 9E noise will continue until human fills in a date; note block shows them how
- This is the missing half of run 104's recommendation (row was pre-existing; note block is new work)

**Action:** Add note section to ops/credential-rotation-schedule.md per run 104 winning-concept.md:
### SUPABASE_ACCESS_TOKEN — Action Required
- Last rotated: unknown — confirm in Supabase dashboard (Settings → API → Service Role Key or Personal Access Tokens)
- Required for: brain connector (GH #394), KB autopopulate GH Action (GH #403), nightly Supabase MCP
- Human action: log the rotation date in the table after confirming with Supabase dashboard

**Impact:** Human has explicit guidance when addressing GH #394. Reduces brain-connector recovery friction.
Run 104's recommendation fully complete.

**Category:** operational
**Effort:** XS (~5 min)

---

### Idea 5: Step 9H v2 — Idempotent subconscious PR pile-up alert

**Evidence:**
- 5 subconscious draft PRs open: #626 (12d), #613 (13d), #611 (14d), #606 (17d), #575 (22d+)
- Prior Step 9H idea KILLED run 100 (non-idempotent design would fire every nightly indefinitely)
- Each PR represents a won idea awaiting human merge decision
- GH #399 blocks autopilot but NOT human PR reviews
- Run 103 backlog notes "Step 9H v2 idempotent PR pile alerter (M-effort, needs idempotency design)"

**Action:** Add Step 9H block to nightly SKILL.md: count subconscious draft PRs; if count ≥ 3 AND newest PR
is ≥ 7 days old, post ONE comment on GH #394 (brain connector issue = human-attention hub) listing PR titles
+ ages. Idempotency: check if existing comment from last 7 days before posting. Max 1 alert per 7-day window.

**Impact:** Human sees aggregated PR pile summary once per week. Encourages batch review instead of individual PR ping.
Solves the "silent accumulation" problem without daily noise.

**Category:** workflow
**Effort:** S (idempotency logic is the new complexity)
