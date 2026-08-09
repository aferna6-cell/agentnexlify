# Ideas — Run 102 (2026-08-09)

## Idea 1: Step 9H — KB Autopopulate Workflow Outcome Monitor
**Evidence:** Run 102 mandate §2: `knowledge-base/INDEX.md` shows "Last compiled: 2026-07-23" — 17 days stale as of 2026-08-09. Step 9G fired on nightly-2026-08-07 ("KB staleness: 15 days — Step 9G triggered"). No new commit to `knowledge-base/` since 2026-07-23. Step 9G's 30s wait exits with "in_progress" and moves on — outcome never verified.
**Action:** Add Step 9H bash block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9G. On the run after Step 9G triggered (KB still stale + `gh run list` shows a recent kb-autopopulate run), check its final conclusion. If failed, comment on GH #403 with specific diagnostic (which secret is likely missing: ANTHROPIC_API_KEY, VOYAGE_API_KEY, SUPABASE_ACCESS_TOKEN). If succeeded but KB still stale, comment different diagnostic.
**Impact:** Closes the Step 9G→outcome gap. Self-healing loop becomes 9F (alert) → 9G (trigger) → 9H (verify). Prevents 17-day stale gaps like current one by surfacing the failure class 24h after trigger.
**Category:** workflow

---

## Idea 2: response_score.py Plan Gate
**Evidence:** `backend/services/response_score.py` (e0e9be6, 2026-08-06) calls Claude 2x per request (lines 134 and 164) with NO plan gate and NO ai_usage_guard check. The insights ROUTER (`backend/routers/insights.py`) has a deliberate "no plan gate" comment — but that comment refers to *reads over existing tables*, not AI calls. `ai_usage_guard.PLAN_BASELINE_TOKENS` already guards all other Claude call sites.
**Action:** Add `ai_usage_guard` check at the top of `response_score.py::score_conversation_response()` so `chatbot` plan gets the base token allocation and `agent_os` gets unrestricted scoring. Match the pattern already in `backend/services/daily_focus.py`.
**Impact:** Prevents `chatbot` tenants from burning AI tokens on response scoring without plan entitlement. Prevents surprise bills on free-tier tenants. Aligns with existing gating pattern.
**Category:** code_health

---

## Idea 3: Close Superseded Subconscious PRs
**Evidence:** Morning digest 2026-08-07 lists 15 open PRs including #625, #626, #613, #611, #606 as subconscious/dependabot drafts. PRs #613, #611, #606 all carry earlier Step 9G iterations that are now superseded by the direct implementation (if merged). PR #625 / #626 are the active Step 9G implementation PRs.
**Action:** After verifying which PR contains the direct Step 9G SKILL.md implementation, close all superseded earlier-Step-9G PRs (#613, #611, #606) with "superseded by #626" comment. Leave #625/#626 open until human merges.
**Impact:** Reduces PR pile from 15 open to ~10. Reduces reviewer confusion about which PR is canonical. Reduces noise in morning-digest.
**Category:** operational

---

## Idea 4: Nexlify Score Token-Burn Guard (response_score + nightly Step 5 criteria)
**Evidence:** memory.jsonl run 101 parking lot: "Nexlify Score token-burn guard (response_score.py ai_usage_guard routing — add to nightly Step 5 criteria)." The `response_score.py` service was added in e0e9be6 (2026-08-06). Nightly Step 5 reviews AI-touching code for plan gate gaps. Adding response_score.py to Step 5's scan pattern would make future AI additions auto-caught.
**Action:** Add `response_score.py` to the nightly Step 5 pattern list in SKILL.md so the nightly review specifically checks it on each run for plan gate presence. This is additive to Idea 2 (Idea 2 fixes the gap; Idea 4 adds monitoring to prevent recurrence).
**Impact:** Prevents future AI service files being added without plan gates by making the detection systematic rather than one-off.
**Category:** workflow

---

## Idea 5: Typed KB Notes Discovery Banner
**Evidence:** memory.jsonl run 101 parking lot: "Typed KB notes discovery banner (KnowledgeSourcesPage.jsx)." KB INDEX.md shows 124 articles, last compiled 2026-07-23. With KB compilation broken (Step 9G/9H chain), tenants don't see fresh knowledge. A discovery banner on KnowledgeSourcesPage.jsx showing KB freshness and article count would surface staleness to tenants directly, not just to the engineering nightly review.
**Action:** Add a banner component to `frontend/src/pages/KnowledgeSourcesPage.jsx` that shows "Knowledge base: {N} articles, last updated {date}" with a visual staleness indicator (green < 3 days, yellow < 7 days, red ≥ 7 days).
**Impact:** Tenant-visible KB health. Makes staleness actionable from the dashboard, not just from ops logs. Low backend cost (read from INDEX.md or a KB metadata endpoint).
**Category:** customer_value
