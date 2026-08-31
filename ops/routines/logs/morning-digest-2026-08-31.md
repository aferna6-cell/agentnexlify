# Morning Digest — 2026-08-31

Generated: 2026-08-31 UTC | Source: ops/routines/logs/

---

## Commits (last 24h) — 18 commits

- `c159976` fix(nightly): remove `__future__` annotations from m8_action_flags service [auto-nightly]
- `47cda00` M8 next actions: staging RLS re-enabled; OAuth/service_role HOLD (#715)
- `b786aeb` M8 staging live proof: RAG+CRM pass; Calendar/Gmail OAuth HOLD (#714)
- `2db4802` M8 deploy readiness: staging runbook + smoke-tenant RAG proof (HOLD) (#712)
- `62ea09c` Add M8 live smoke runner + record staging proof blockers [skip ci] (#711)
- `a36f97a` Milestone 8 finalization: Calendar/CRM production data plane (#710)
- `41aecb5` M8: Calendar + CRM Business Actions (tools, safety, eval — flags OFF) (#709)
- `f2fe438` docs: mark migration 198 applied on prod [skip ci] (#708)
- `39925c2` Merge PR #707 — milestone7-rag-ready
- `1c705ac` docs(m7): record M6 RAG OFF/ON regression gate numbers
- `741f10c` fix(m7): honor RAG abstention, independent holdout, calibrated refusal
- `e2b7670` fix(m7): fail-open RAG attach so retrieval cannot take down a turn
- `2413576` docs(m7): publish labelled-only RAG metrics + scoring caveats
- `2f3adeb` fix(m7): honest RAG metrics, mixed-corpus isolation, policy-bypass tests
- `18652f3` feat(m7): tenant RAG — eval first, BM25 retrieval, default-off flag
- `1a9c633` Merge PR #705 — M6 decision intelligence complete
- `067dcf3` chore(m6): drop stale eval snapshots, war-room router decision record [skip ci]
- `042381c` feat(m6): complete decision intelligence — eval harness, semantics, router bakeoff

**Signal:** Heavy M7→M8 push. M8 staging is partially live but gated on Calendar/Gmail OAuth + service_role wiring. Nightly auto-fixed a `__future__` annotation violation.

---

## Issues — Open / Recently Updated

### Blockers (human-action-required)
- **#403** [CRITICAL] Set `ANTHROPIC_API_KEY` in GH Actions secrets — blocks autopilot loop + KB autopopulate — open since 2026-07-09
- **#684** Brain connector 33 days stale — last run 2026-07-23 — `human-action-required` — *updated today* (nightly commented)

### Security / Billing (unresolved)
- **#669** [SECURITY] 95 routers missing `Depends(block_demo_role)` on mutating endpoints — `ai-ready`, open since 2026-08-20
- **#687** [MEDIUM] Voice addon double-billing gap: no cancellation on tenant upgrade to agent_os — open since 2026-08-26

### Code Quality (nightly-generated)
- **#689** Silent exception blocks + misleading param name in `churn_watch.py` / `appointment_booker.py` — `risk:low` — open since 2026-08-26

### Digest backlog (not actioned)
- #692 (2026-08-28), #691 (2026-08-27), #688 (2026-08-26), #685 (2026-08-25) — digest issues accumulating unread/unclosed

---

## Open PRs Needing Action (10 open)

| # | Title | Age | Status |
|---|-------|-----|--------|
| #716 | M8 HOLD: staging RLS on; service_role wiring; step 3 gate | 0d | Draft — needs Calendar OAuth resolution |
| #713 | subconscious run 114 — Step 9K stale PR audit + Step 9J fix | 0d | Draft — awaiting review/merge |
| #703 | feat(evals): send/L2 claim-then-execute via FakeGmailPort | 1d | Draft |
| #693 | feat(agent-os): action layer, send_email, eval harness | 3d | Draft — last updated 2026-08-30 |
| **#679** | **Dependabot: bump eslint 10.7→10.9** | **7d** | **Ready to merge (not draft)** |
| #690 | docs(outreach): record live Instantly campaign templates | 5d | Draft |
| #683 | subconscious runs #110-111 — Step 9J + block_demo_role hook | 7d | Draft |
| #653 | subconscious runs 102-110 — Step 9J impl + GH #669 proposal | 19d | Draft — stale |
| **#580** | **Dependabot: bump actions/checkout 4→7** | **34d** | **Ready to merge (not draft)** |
| #575 | Tenant-silence ops alert + Managed Agents Phase 0 prep | 38d | Draft — very stale |

**Action:** #580 and #679 are not drafts — merge or close. 5+ open subconscious PRs confirms Step 9K threshold already hit.

---

## Subconscious Recommendation

**Run 113 (2026-08-30):** Add Step 9K to nightly SKILL.md — stale subconscious PR audit (warn ≥3, escalate ≥5 or >60d). Also fix Step 9J Dependabot detection (switch from `list_pull_requests(creator=...)` to `search_pull_requests(author:app/dependabot)`). Both in same SKILL.md edit. PR #713 implements this — review and merge.

**Run 111 (2026-08-29):** Step 9J @dependabot rebase trigger for `mergeable_state: unknown`. Already in PR #683.

---

## KB Health

Last compile: 2026-08-26 19:28 — 4 articles (competitors/ai_llm/frontier_ai/growth). No run today yet. Embedding skipped (no VOYAGE_API_KEY). FTS fallback active. 124 articles indexed.

---

## Top 3 Priorities Today

### 1. Unblock M8 — Calendar/Gmail OAuth + service_role wiring
- PR #716 is the gate. M8 staging has RLS enabled, RAG+CRM passing.
- Blocked on: Calendar/Gmail OAuth creds in Railway + service_role key injection for RLS bypass scripts.
- Step 3 gate must pass before M8 hits prod.

### 2. Fix the two non-draft Dependabot PRs (#580, #679)
- `actions/checkout 4→7` and `eslint 10.7→10.9` — both not draft, both CI-passing (presumably).
- Step 9J @dependabot rebase fix (PR #683) would have auto-handled these. Instead they aged 7–34 days.
- Merge both or close if superseded.

### 3. Address GH #669 — 95 routers missing `block_demo_role`
- Security gap labeled `ai-ready` — subconscious has a proposal in PR #653.
- PR #683 claims to add a pre-commit hook for this. Not merged yet (7d open).
- This + #687 (double-billing) are the two live business-risk issues.

---

## Standing blockers (human-action-required)

- `ANTHROPIC_API_KEY` missing in GH Actions (#403) — breaks KB cron + autopilot loop
- `SUPABASE_ACCESS_TOKEN` not set in Railway — blocks brain connector + Step 9E rotation tracking (#684)
- Calendar/Gmail OAuth creds not provisioned in Railway — M8 HOLD gate

---

*Caveman summary: M7 done. M8 staging live but OAuth blocked. Two Dependabot PRs rotting ready-to-merge. Security gap (#669) + billing gap (#687) unaddressed. Set the three Railway secrets to unblock everything.*
