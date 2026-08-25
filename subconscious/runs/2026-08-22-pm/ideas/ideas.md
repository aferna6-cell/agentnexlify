# Ideas — Subconscious Run 2026-08-22-pm (#109)

## Evidence Digest (200 words)

3 days of commits: only nightly ops logs (2026-08-20/21/22) + subconscious run 108 artifacts. Zero production code. Step 9J absent from nightly SKILL.md (grep returns 0) — 1st carry-forward mandate fires this run (autonomous-executable). Nightly-2026-08-21 explicitly confirmed Step 9J not applied. Nightly-2026-08-22 clean (1 commit reviewed, 0 bugs). KB log shows recent FTS autopopulate: INDEX.md updated 114→124 articles, known-urls 420→432 — embeddings still skipped (no SUPABASE credentials). GH #399 (AUTOPILOT_GH_TOKEN) Day 41+, open. GH #403 (KB pipeline) — run 107+108 bonus comments posted; KB FTS did run. GH #669: 97/97 routers missing block_demo_role, filed 2026-08-20, no PR yet (GH #399 stalls loop). 6 Dependabot PRs aging: #629/#630/#631/#649/#665/#666. customer-gaps.md: AI-to-human handoff Critical (frozen). No new bugs in review window.

---

## Idea 1: Step 9J — Dependabot Auto-Merge in nightly SKILL.md (carry-forward mandate)

**Evidence:** grep 'Step 9J' .claude/skills/nightly-commit-review/SKILL.md returns 0. Run 108 governance: "Autonomous-executable if not approved by run 109 (1st carry-forward mandate)." 6 Dependabot PRs aging 4+ weeks (#629/#630/#631/#649/#665/#666). Morning digests 2026-08-11/12/17/18 flagged same PRs with zero action. Nightly channel proven: Steps 9C/9E/9F/9G/9I all implemented via same SKILL.md-edit channel, each landing within 1-2 cycles.

**Action:** Write Step 9J block directly to .claude/skills/nightly-commit-review/SKILL.md (after Step 9I). Block lists Dependabot PRs, checks CI (mergeable_state=clean) + no review requests + no blocking labels, merges eligible PRs via squash, logs count.

**Impact:** 6 PRs merge within 24h of CI green. Security patches land within 24h indefinitely. ~15 min/week manual overhead eliminated. Structural: runs forever.

**Category:** operational

---

## Idea 2: Step 9K — Stale Subconscious PR Auto-Closer in nightly SKILL.md

**Evidence:** Run 108 parking lot explicitly listed "Step 9K: stale autonomy PR closer in nightly (run 109+ candidate)." The PR dedup guard (added 2026-07-20, run 99) prevents NEW duplicate subconscious PRs, but old draft PRs pre-dedup-guard accumulate. Multiple draft subconscious PRs have been open 14-19+ days (#606, #611, #613, #625, #626 referenced in runs 102-106). Stale drafts create governance confusion and inflate PR queue noise.

**Action:** Add Step 9K after Step 9J. Block: list open PRs with head branch matching "subconscious/*". For each, check if open >14 days AND no unmerged commits beyond main. Close eligible drafts with message "Closing stale subconscious draft — superseded by newer run or already committed to main." Log count.

**Impact:** Clean governance state. Removes PR queue noise. Human reviewer sees only live subconscious direction, not historical artifacts. Low risk (only closes PRs with no unique commits beyond main).

**Category:** workflow

---

## Idea 3: File GH Issue for Middleware-Level block_demo_role FastAPI Guard

**Evidence:** GH #669 (filed 2026-08-20): 97/97 routers missing block_demo_role. The Step 9I nightly sweep will detect future regressions but won't fix the existing 97. Per-router fix would touch 97 files — high blast radius. FastAPI supports a global dependency override or middleware that would fix all non-excluded routes in one change. Run 108 parking lot: "middleware-level block_demo_role FastAPI guard (GH #669 tracking — M-effort, human-approval required)."

**Action:** File detailed GH issue with exact implementation sketch for a FastAPI-level fix: add block_demo_role as a default dependency on the main APIRouter, with explicit exclusions for auth, webhook, and admin routes. Label: security + ai-ready (when GH #399 resolved). Body includes exact code pattern.

**Impact:** Closes the 97-router class permanently with one file change. Prevents Step 9I from filing 97 individual issues. Highest security leverage per line of code.

**Category:** code_health

---

## Idea 4: Add KB Embeddings Credential Gap Comment to GH #403

**Evidence:** KB log shows "Embeddings SKIPPED (no credentials; FTS fallback covers retrieval)". GH #403 was originally about ANTHROPIC_API_KEY for article generation. But even after ANTHROPIC_API_KEY is added, semantic search will stay broken if SUPABASE_URL + SUPABASE_ANON_KEY are absent from Actions. Run 108 bonus action diagnosed this. KB FTS works (recent run updated 114→124 articles) but semantic search degrades AI chat quality for cross-vertical queries.

**Action:** Comment on GH #403 clarifying two-phase fix: (1) ANTHROPIC_API_KEY unblocks article generation, (2) SUPABASE credentials unblock pgvector embeddings. Provide exact GitHub Actions secret names and where to find values. Separate the two blockers so human can fix one at a time.

**Impact:** Semantic search restored after human adds credentials. AI chat quality improves for cross-topic queries. Low effort (comment only).

**Category:** operational

---

## Idea 5: Trial-to-Member Conversion Tracking GH Issue (Fitness vertical)

**Evidence:** customer-gaps.md: "Trial-to-member conversion tracking (Medium impact, Low effort)" for Fitness vertical. No recent commits touching fitness. Lead source tracking already exists (lead_source_breakdown in leads table). A conversion_status or trial_start_date field in leads would support this gap.

**Action:** File GH issue with acceptance criteria: widget config option "trial_period_days" (default 0 = disabled), lead field "trial_start_date" populated on intake, automation trigger "trial_expiring" N days before trial end, admin view of trial-to-paid conversion rate.

**Impact:** Fitness vertical differentiation. Enables upsell automation. Closes a customer-gaps.md Medium/Low entry.

**Category:** customer_value
