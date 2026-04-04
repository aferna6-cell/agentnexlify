# Candidate Ideas — 2026-04-04

### Idea 1: Fix the failing test (test_resend_webhook_route_is_registered)
**Evidence:** `python3 -m pytest` shows 1 failure: `test_resend_webhook_route_is_registered`. This was likely introduced by the resend webhook signature enforcement change in commit `c73a1ff`. A red test suite erodes trust in all other tests.
**Action:** Read the failing test, understand what it expects, fix the test or the code to align with the new webhook signature enforcement behavior.
**Impact:** Green test suite restored. CI/CD pipeline unblocked. All future PRs can rely on tests passing.
**Category:** code_health

### Idea 2: Apply the 4 existing skill updates flagged by weekly discovery
**Evidence:** `docs/skill-discovery/2026-04-04.md` flagged 4 stale skills: feature-build (migration number says "after 032", now at 081), schema-guard (missing RLS policy verification), debug-api (missing orphan session diagnostic), migration-workflow (missing duplicate number warning).
**Action:** Update all 4 skill SKILL.md files with the specific additions noted in the discovery report.
**Impact:** Skills produce correct guidance. Prevents future RLS silent failures (the #1 bug class found in the MTOptions audit). 15-30 min saved per skill invocation that would have hit stale info.
**Category:** workflow

### Idea 3: Populate the 4 empty KB categories via /kb-discover
**Evidence:** `knowledge-base/INDEX.md` shows 4 of 7 categories have zero articles: AI/LLM Developments, Small Business SaaS, Technical Patterns, Regulations & Compliance. The KB was just built today with only 3 seed articles from existing docs.
**Action:** Run `/kb-discover ai_llm technical regulations small_biz_saas` to populate the empty categories with fresh web research.
**Impact:** KB becomes useful for queries across all categories. Currently queries about AI models, compliance, or technical patterns return nothing.
**Category:** workflow

### Idea 4: Build the AI-to-human handoff feature
**Evidence:** `customer-gaps.md` lists "AI-to-human handoff" as the #1 cross-industry open gap with CRITICAL impact. Every vertical simulation flagged it. The competitive landscape article notes Intercom/Drift/Freshchat all have this.
**Action:** Design and implement a handoff mechanism: AI detects when it can't resolve a query, flags the conversation for human takeover, notifies the team member, preserves context.
**Impact:** Closes the most critical customer gap. Affects all verticals. Directly impacts customer satisfaction and lead conversion.
**Category:** customer_value

### Idea 5: Add conftest.py to consolidate duplicated test fixtures
**Evidence:** The codebase audit (Agent 5 report) found `_setup_table_mock` helper duplicated identically across 4+ test files, and `test_client` fixture duplicated with slight variations. `test_auth_endpoints.py` is missing `os.environ["TESTING"] = "1"` unlike other test files.
**Action:** Create `tests/conftest.py` with shared fixtures: `_setup_table_mock`, `test_client`, `mock_settings`. Remove duplicates from individual test files. Add missing TESTING env var.
**Impact:** Test maintenance burden drops. New test files get fixtures for free. Reduces ~200 lines of duplication. Prevents inconsistency bugs.
**Category:** code_health
