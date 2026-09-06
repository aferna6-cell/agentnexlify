# Candidate Ideas — Run 115 (2026-09-05)
<!-- SUPERSEDED (2026-09-05-pm): AM draft; file-level grep detection. Canonical spec: subconscious/runs/2026-09-05-pm/winning-concept.md -->

## Idea 1: Add AI Usage Guard Checklist to compound-engineering SKILL.md
**Evidence:** PRs #792-#799 retroactively metered 6 AI endpoints in 3 days — widget_guard.screen, categorize_conversation, extract_action_items, extract_tags, voice call summaries, sms_agent.reply. Each required substantial new test files (498-1726 tests each). The compound-engineering skill has no explicit reminder to check for reserve/record/release metering before merging AI-calling code.
**Action:** Insert a "Pre-merge AI metering checklist" section into `.claude/skills/compound-engineering/SKILL.md` — grep for `client.messages.create` / `llm_runtime.call_claude` and verify ai_usage_guard is present before committing.
**Impact:** Prevents future AI endpoints shipping without metering, avoiding retroactive multi-day metering sprints.
**Category:** workflow

---

## Idea 2: Fix Step 9J Token Budget — Batch Dependabot PR Checks
**Evidence:** nightly-2026-09-05 shows "17 Dependabot PRs not individually checked this run (token budget)". Step 9J only triggered rebase on 2 of 19 Dependabot PRs. The rebase detection is working but budget exhaustion means 17 PRs accumulate without attention.
**Action:** Edit Step 9J in `.claude/skills/nightly-commit-review/SKILL.md` — add batch limit and prioritize oldest-stale PRs first; also add a count-only summary log when budget is tight.
**Impact:** Prevents Dependabot backlog accumulation; ensures at least oldest PRs get attention each night.
**Category:** operational

---

## Idea 3: Invoke /god-class-splitter on os_tool_executions.py
**Evidence:** `backend/services/os_tool_executions.py` is 783 lines (threshold: 600L, Rule 9). Last commit was `f22ef04` (Billing Automation v1, PR #765). The file has been stable ~4-5 days; prior run 114 mandate noted it as candidate if stable 4d+. The file handles multiple concerns: tool execution, state management, billing, and result formatting.
**Action:** Split `os_tool_executions.py` into focused modules: `os_tool_executor.py` (core execution), `os_tool_billing.py` (billing/reserve/release), `os_tool_state.py` (state management) — each under 300L.
**Impact:** Reduces bug surface area; enables parallel editing without merge conflicts; aligns with Rule 9 (god class factor-out).
**Category:** code_health

---

## Idea 4: Add Step 9L — AI Metering Coverage Nightly Check
**Evidence:** PRs #792-#799 retroactively metered 6 AI endpoints in 3 days. Pattern: AI-calling code ships without reserve/record/release metering, then requires a dedicated retroactive sprint. Same class problem as block_demo_role (solved by Step 9I — auto-sweep found demo-role gaps). The nightly grep-and-file mechanism is proven (Steps 9C, 9E, 9F, 9G, 9I, 9K all work). Today's nightly confirmed Steps 9J and 9K fired correctly.
**Action:** Add Step 9L block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9K. Grep `backend/routers/` and `backend/services/` for files that import/call Claude API (anthropic.Anthropic, llm_runtime.call_claude, client.messages.create) without corresponding usage guard (reserve/record/release or ai_usage_guard dependency). If violations found: check for existing open GH issue by filename; if none, file issue with labels `ai-ready + code_health`.
**Impact:** Catches AI metering gaps at night before they ship; eliminates multi-day retroactive sprints; equivalent AI safety enforcement to block_demo_role sweep.
**Category:** code_health

---

## Idea 5: Trial-to-Member Conversion Tracking (Fitness Vertical)
**Evidence:** `docs/dev-knowledge/customer-gaps.md` lists "Fitness vertical: trial-to-member conversion (Medium impact, Low effort)". The widget already captures leads and appointments. Member retention tracking is noted as a gap. No conversion funnel exists for fitness studio tenants.
**Action:** Add a `conversion_events` table (migration 155_conversion_events.sql), a `/api/conversions` endpoint (POST trial→member), and a Fitness Dashboard page showing trial count, conversion rate, and 30-day trend.
**Impact:** Enables fitness studio tenants to track ROI of the widget; addresses explicit customer gap; differentiates from GoHighLevel on fitness vertical.
**Category:** customer_value
