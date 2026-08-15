# Run 104 — Candidate Ideas (2026-08-15)

## Evidence base
- Run 103 winner (Step 9C age gate) applied by nightly-commit-review 2026-08-15 (commit 60499dd) — same-day implementation
- Step 9E today: "SUPABASE_ACCESS_TOKEN: unknown state (not yet set in rotation schedule)"
- Brain connector 23 days stale (threshold: 14 days); GH #394 open
- route-security-guard-audit SKILL.md still MISSING (2nd carry-forward, run 102 winner)
- scoring_config.py (`/api/v1/scoring`) has NO `ai_usage_guard` or `block_demo_role` — new finding this run
- AUTOPILOT_GH_TOKEN still expired (GH #399, 37+ days)
- KB 23 days stale; Step 9G triggered kb-autopopulate.yml today
- bug-patterns.md: "Silent-green automation" — paying tenant widget missing 5+ weeks unnoticed (2026-07-23)

---

## Idea 1 — Add SUPABASE_ACCESS_TOKEN to credential rotation schedule

**Category:** operational_efficiency  
**Effort:** XS (~5 min)  
**Confidence:** HIGH  
**Source:** Fresh evidence — today's Step 9E flag

**Problem:** `ops/credential-rotation-schedule.md` does not include SUPABASE_ACCESS_TOKEN. Step 9E explicitly flagged "SUPABASE_ACCESS_TOKEN: unknown state (not yet set in rotation schedule)." The token is used by brain connector and KB autopopulate. Brain connector is 23 days stale; SUPABASE_ACCESS_TOKEN may be a contributing factor. Without a schedule entry, Step 9E cannot alert on staleness and the token can silently expire with no automated warning.

**Proposed action:** Add SUPABASE_ACCESS_TOKEN row to `ops/credential-rotation-schedule.md`:
- Name: SUPABASE_ACCESS_TOKEN
- Interval: 90 days (conservative; Supabase personal tokens default to 90-day or never-expires depending on project settings)
- Last rotated: unknown (to be confirmed by human)
- Owner: human (requires Supabase dashboard access)
- Used by: brain connector, KB autopopulate (GH Actions), Supabase MCP in nightly
- Alert threshold: 76 days (8% buffer = 14-day warning window, same pattern as AUTOPILOT_GH_TOKEN)

**Impact:** Step 9E will track this token every nightly run. If it expires, Step 9E surfaces a WARNING before the alert. Closes the direct gap flagged by today's automated monitoring.

**Status:** AUTONOMOUS-EXECUTABLE — doc-only edit to a markdown file, same class as Steps 9F/9G/9C

---

## Idea 2 — Create route-security-guard-audit SKILL.md (2nd carry-forward)

**Category:** code_health  
**Effort:** S (~30 min)  
**Confidence:** HIGH  
**Source:** Carry-forward from run 102; new confirming evidence from run 104

**Problem:** No systematic checklist for auditing router files for missing `ai_usage_guard` and `block_demo_role` guards. Run 102 documented the gap for appointment_briefs.py (GH #643). Run 104 found the same gap in `scoring_config.py` (`/api/v1/scoring`) — demo tenants can modify scoring configuration because `block_demo_role` is absent. This is now the second confirmed instance of the same class of problem with no SKILL.md to prevent recurrence.

**Proposed action:** Write `.claude/skills/route-security-guard-audit/SKILL.md` — 6-step audit checklist: (1) list all router files, (2) grep for missing `block_demo_role`, (3) grep for missing `ai_usage_guard`, (4) score each endpoint by risk tier, (5) emit fix list, (6) track in GH issues. Fully specified in `subconscious/runs/2026-08-11-pm/winning-concept.md`.

**Impact:** Prevents the "scoring_config.py class" of gap from recurring. Every new router can be audited before merge.

**Status:** CARRY-FORWARD (2nd cycle) → PENDING-APPROVAL — requires human review of SKILL.md content. At 3rd carry-forward (run 105), escalates to AUTONOMOUS-EXECUTABLE per subconscious precedent.

---

## Idea 3 — Add block_demo_role to scoring_config.py

**Category:** security  
**Effort:** S (~20 min)  
**Confidence:** HIGH  
**Source:** New finding this run (scoring_config.py audit)

**Problem:** `backend/routers/scoring_config.py` at `/api/v1/scoring` imports only `_get_current_tenant` and `require_role`. It has no `block_demo_role` dependency. Demo tenants can call `POST /api/v1/scoring` to create scoring factors, `PUT /api/v1/scoring/{id}` to modify them, and `DELETE /api/v1/scoring/{id}` to delete them. Same class of problem as #643 (appointment_briefs.py).

**Proposed action:** Add `block_demo_role` as a FastAPI dependency to the create, update, delete endpoints in `scoring_config.py`. Optionally add `ai_usage_guard` if scoring factor operations are LLM-assisted.

**Impact:** Closes a direct security gap — demo tenants cannot manipulate scoring configuration.

**Status:** PENDING-APPROVAL — code change, needs PR + review. This is the second known instance of this class of problem; the route-security-guard-audit SKILL.md (Idea 2) would prevent a third.

---

## Idea 4 — Step 9I: Paying-tenant 0-conversation alert

**Category:** operational_efficiency  
**Effort:** M (~45 min)  
**Confidence:** MEDIUM  
**Source:** bug-patterns.md "Silent-green automation" entry (2026-07-23)

**Problem:** bug-patterns.md documents a paying tenant whose widget was missing for 5+ weeks with no automated alert. Step 9 currently monitors brain connector health, credential rotation, and KB staleness, but has no step checking whether paying tenants are receiving widget conversations. A tenant with 0 conversations for 7+ days may have a broken embed.

**Proposed action:** Add Step 9I to nightly SKILL.md: query Supabase for paying tenants (`subscriptions` table, plan = chatbot or agent_os) with 0 conversations in last 7 days. Alert if any found. Headless execution concern: Supabase MCP may not be available in automated nightly sessions — would need to route through GH Actions or use a different data source.

**Impact:** Catches the "silent-green" class of failure before 5-week gap accumulates.

**Status:** PENDING-DESIGN — Supabase MCP availability in headless nightly sessions is unconfirmed. Parking lot until headless Supabase access is proven.

---

## Idea 5 — Wire PR #653 draft → ready-for-review

**Category:** operational_efficiency  
**Effort:** XS (~2 min)  
**Confidence:** HIGH  
**Source:** improvement-backlog run 103 (BONUS-ACTION); nightly 9D confirms #653 still draft

**Problem:** GH #643 (appointment_briefs.py missing block_demo_role) is blocked on PR #653, which is still in draft. Promoting it to ready-for-review unblocks the human review+merge cycle and closes a known security issue.

**Proposed action:** Call `mcp__github__update_pull_request` to set `draft: false` on PR #653.

**Status:** ONE-OFF ACTION — not a persistent system improvement. Lower leverage as a "winner" than a systemic change. Can execute as a BONUS-ACTION alongside the winner.

---

## Ranking

| Rank | Idea | Category | Effort | Status |
|------|------|----------|--------|--------|
| 1 | Add SUPABASE_ACCESS_TOKEN to rotation schedule | operational | XS | AUTONOMOUS-EXECUTABLE |
| 2 | route-security-guard-audit SKILL.md | code_health | S | CARRY-FORWARD (2nd) |
| 3 | scoring_config.py block_demo_role | security | S | PENDING-APPROVAL |
| 4 | Step 9I paying-tenant 0-conversation alert | operational | M | PENDING-DESIGN |
| 5 | Wire PR #653 → ready-for-review | operational | XS | BONUS-ACTION (not winner material) |
