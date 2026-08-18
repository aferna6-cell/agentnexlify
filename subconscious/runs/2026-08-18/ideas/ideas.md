# Ideas — Run 107 (2026-08-18)

## Evidence Snapshot
- Step 9I not in SKILL.md — 1 carry-forward run (run 106 winner, escalates at run 108)
- Nightly-2026-08-18 ran Step 9I sweep informally — 100+ pre-existing violations, logic confirmed correct
- 4 Dependabot PRs (#629/#630/#631/#649) aging 7-14 days, CI green — flagged every morning digest
- GH #399 (AUTOPILOT_GH_TOKEN): Day 38+, blocking issue-to-pr-loop
- GH #403 (ANTHROPIC_API_KEY in GH Actions): 38d+, blocking KB GH Actions CI path
- SUPABASE_ACCESS_TOKEN last_rotated date not filled by human despite run 104 winner
- `ops/credential-rotation-schedule.md` shows `last_rotated: unknown — not yet set`
- Recent bug: client_id/tenant_id confusion in connector_awareness.py (2026-08-01)
- All project invariants: PASS
- 7 commits last 3 days: all automation artifacts, zero product code

---

## Idea 1 — Step 9I SKILL.md Formalization (Mandate Carry-Forward)

**Category:** Workflow Automation  
**Evidence:** Run 106 winner; escalates to autonomous-executable at run 108 if not approved; nightly-2026-08-18 confirmed the sweep logic works (ran informally, correctly skipped bulk-filing pre-existing 100+ violations)  
**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` — add Step 9I block after existing Step 9H  
**Step 9I logic:**
- grep `backend/routers/` for `@router.(post|put|patch|delete)` per file
- For each file with mutating routes: check if `block_demo_role` appears in `Depends(...)` imports
- Skip: files with only GET routes, `admin/` prefix, webhook routes (`stripe_webhooks`, `twilio_webhooks`, `resend_webhooks`), public widget routes
- Dedup: search existing open GH issues with label `security` + filename before filing
- File issue with labels `security`, `ai-ready` if new violation found
**Confidence:** HIGH — mandate-triggered, channel proven (9C→9H all implemented same channel)

---

## Idea 2 — `dependabot-merge-runner` Skill

**Category:** Workflow Automation  
**Evidence:** 4 Dependabot PRs (#629/#630/#631/#649) explicitly labeled "safe to merge" in every morning digest for 7-14 days; zero automated action; skill-discovery-2026-08-17 formally proposed it; no GH #399 dependency (skill merges via mcp__github__merge_pull_request, not autopilot loop)  
**Action:** Create `.claude/skills/dependabot-merge-runner/SKILL.md`  
**Logic:** List Dependabot PRs → check CI status → merge CI-green PRs with no failing checks → skip CI-red PRs (label `blocked-ci`) → log to `ops/routines/logs/dependabot-merge-YYYY-MM-DD.md`  
**Confidence:** HIGH — evidence across 7 days of morning digests, no blockers

---

## Idea 3 — GH #399 Escalation Comment (Mechanism Exhausted)

**Category:** Operational  
**Evidence:** Day 38+; every nightly review mentions it; runs 9E/9F/9G all posted comments; previous comment-posting attempts documented  
**Action:** Post another targeted comment on GH #399 with exact token rotation steps  
**Problem:** Information is not the bottleneck at day 38. Human has seen this 38+ times. Behavior bottleneck, not information bottleneck.  
**Confidence:** LOW for impact — mechanism exhausted

---

## Idea 4 — `stale-autonomy-pr-closer` Skill

**Category:** Workflow Automation  
**Evidence:** 5 stale draft autonomy PRs (#606 20d, #611 18d, #613 17d, #626 15d, #653 6d); skill-discovery-2026-08-17 formally proposed it  
**Timing risk:** GH #399 resolution (autopilot loop restart) would cause PR merge cascade, potentially superseding most of these PRs. Building a closer now may be premature — the situation resolves differently if #399 is fixed.  
**Confidence:** MEDIUM — evidence strong but timing risk real

---

## Idea 5 — KB Autopopulate Commit Verification

**Category:** Operational  
**Evidence:** KB log shows GH Actions path blocked (#403); local session ran KB successfully (114→124 articles, 10 new articles); "No commit — main session commits" note at end of log — KB session committed but may not have pushed  
**Action:** Add explicit `git push` after KB autopopulate commit, verify via `git log origin/main..HEAD`  
**Problem:** Run 105 already fixed this for subconscious SKILL. KB autopopulate script (`scripts/daily/kb-autopopulate.sh`) may also lack a push step.  
**Confidence:** MEDIUM — narrow fix, but narrower than Step 9I mandate
