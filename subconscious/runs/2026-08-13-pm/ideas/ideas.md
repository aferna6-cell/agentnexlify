# Run 103 — Candidate Ideas (2026-08-13-pm)

Evidence window: 2026-08-11 → 2026-08-13
Mandate checks completed before ideation.

---

## Mandate Checks (Run 103)

1. **response_score.py ai_usage_guard** → RESOLVED. File is `backend/services/response_score.py` (service layer, not router). No block_demo_role needed at service layer. Mandate P2 was based on wrong file path assumption.
2. **PR pile-up** → UNCHANGED. #626 open 10+ days. Dependabot #649, #629, #630, #631 still pending (9+ days). AUTOPILOT_GH_TOKEN NOT rotated.
3. **KB staleness** → STILL BLOCKED. 21 days stale. Step 9G triggers kb-autopopulate.yml but ANTHROPIC_API_KEY missing (#403) blocks actual compile.
4. **route-security-guard-audit SKILL.md** → NOT CREATED. Human has NOT merged PR #653 (2 days open, awaiting review). Carry-forward cycle 2.
5. **GH #643 status** → STILL OPEN. 7 days, no linked PR, ai-ready+security labels. Autopilot stalled 5/5 failures (#399).
6. **Dependabot PRs** → STILL PENDING. All 4 aging 9-10 days.

---

## 5 Candidate Ideas

### Idea 1 — Fix appointment_briefs.py security guards (code_health, XS, HIGH)

**Evidence:**
- `backend/routers/appointment_briefs.py` confirmed: `Depends(_get_current_tenant)` only. `block_demo_role`, `ai_usage_guard`, `plan_gate` ALL absent.
- GH #643 open 7 days, labeled `ai-ready` + `security` + `medium-risk`, no linked PR.
- Autopilot 5/5 failures — cannot self-fix via normal queue (#399 expired token).
- Pattern proven: c204af2 (2026-08-08) applied identical guard to billing_usage.py as existing-file code edit — same execution path available.
- nightly-2026-08-13 identifies #643 as top open blocker.
- route-security-guard-audit SKILL.md (proposed run 102) already documents the exact steps needed.

**Proposal:** Apply `block_demo_role` guard to appointment_briefs.py router endpoints. Add `ai_usage_guard` call inside the handler before Claude API call. Add structural test in `test_plan_gating_new_plans.py`. Mark AUTONOMOUS-EXECUTABLE so nightly applies next cycle.

**Risk:** LOW. Same pattern as c204af2 which landed cleanly.

---

### Idea 2 — route-security-guard-audit SKILL.md carry-forward (code_health, S, HIGH)

**Evidence:**
- PR #653 open 2 days — SKILL.md content already written and reviewed.
- Human has not merged. Awaiting approval.
- Run 102 winner — still pending_approval status.
- 3 commits in 48h (cbbaae5, c204af2, 228203d) established the pattern need.

**Proposal:** Carry forward as parking lot item — cycle 2. Not yet at 3-cycle escalation threshold for direct implementation.

**Note:** Fixing #643 (Idea 1) is higher leverage than creating the skill that would catch future #643s. Do both, but in the right order.

---

### Idea 3 — Add SUPABASE_ACCESS_TOKEN to 9E credential tracking (operational, XS, HIGH)

**Evidence:**
- nightly-2026-08-13 Step 9E: SUPABASE_ACCESS_TOKEN status shows "UNKNOWN — not yet set"
- #403 blocker: missing CI secrets includes SUPABASE_ACCESS_TOKEN + ANTHROPIC_API_KEY + VOYAGE_API_KEY
- Current 9E only tracks AUTOPILOT_GH_TOKEN rotation date
- Step 9E could proactively alert on SUPABASE_ACCESS_TOKEN presence via GH Secrets API

**Proposal:** Add SUPABASE_ACCESS_TOKEN check to nightly SKILL.md Step 9E credential tracking. One additional grep/API call alongside existing AUTOPILOT_GH_TOKEN check. Fits SKILL.md-edit autonomous channel.

---

### Idea 4 — Update feature-build SKILL.md with 5-file standard pattern (workflow, XS, MEDIUM)

**Evidence:**
- Parking lot P3 from run 102: "two commits (e0e9be6, 4853c31) follow same pattern"
- skill-discovery-2026-08-10 update proposal: e0e9be6 and 4853c31 both follow router+service+model+test+migration 5-file pattern
- Fits SKILL.md-edit autonomous channel
- Low evidence density — same as run 102 assessment

**Proposal:** Add 5-file standard pattern documentation to feature-build SKILL.md. Low-effort, fits autonomous execution.

---

### Idea 5 — Create pr-backlog-triage SKILL.md (workflow, S, MEDIUM)

**Evidence:**
- Parking lot P1 from run 102: 10 open PRs, 4 dependabot PRs aging 9+ days
- skill-discovery-2026-08-10 explicit proposal
- PR pile-up confirmed still present (all 4 dependabot PRs still pending)
- Morning digest 2026-08-12: "PR debt accumulating"

**Proposal:** Create `.claude/skills/pr-backlog-triage/SKILL.md` for labeling + classifying open PRs. Conservative: classify + label + summary, no auto-merge as default.

---

## Ranking

| Rank | Idea | Category | Effort | Confidence |
|------|------|----------|--------|------------|
| 1 | Fix appointment_briefs.py guards | code_health | XS | HIGH |
| 2 | route-security-guard-audit carry-forward | code_health | parking lot | HIGH |
| 3 | Add SUPABASE_ACCESS_TOKEN to 9E | operational | XS | HIGH |
| 4 | Update feature-build 5-file pattern | workflow | XS | MEDIUM |
| 5 | Create pr-backlog-triage SKILL.md | workflow | S | MEDIUM |
