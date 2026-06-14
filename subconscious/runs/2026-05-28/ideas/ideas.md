# Ideation — Run 37 (2026-05-28)

## Evidence Digest

**What changed (last 3 days):**
- PR #188 (Agent OS rehaul, Groups A+B+C) merged 2026-05-27 — massive new feature: SMS/email/Facebook outbound mirrors, inbound bridge config UI, replay protection (os_outbound_log, migration 130). 152 Agent OS tests + 498 total green.
- `bca2082` (2026-05-28): 3rd test-mock-repair commit in 6 days — aligned stale filter-chain mocks after `.not_.is_()` → `.filter()` cleanup migration. Pattern: `5f2cd2b` (21 stale patches after local_seo split, 2026-05-22), `4afb3cf` (stale import same split, 2026-05-22), `bca2082` (2 mock chains after API-cleanup migration, 2026-05-28).
- Nightly review today: "no issues found" — explicitly labeled run 36 subconscious artifact as "Documentation/ideas only. No production code changes." Did NOT autonomously create post-split-test-repair SKILL.md.

**What's missing:**
- post-split-test-repair SKILL.md: MISSING (run 36 winner — nightly review didn't act)
- GH #181: STILL OPEN (26+ days) — `AMOUNT_TO_PLAN` confirmed missing `15000→autopilot`, `25000→professional`. `test_billing_amount_to_plan.py:38-44` certifies broken state.
- Moratorium Items A/B/D: still MISSING (day 24+)
- email_sequences.py: 1255L, run 35 winner unimplemented

**What's working:**
- Agent OS clean: webhook security present (Twilio HMAC + email signatures verified in os_inbound.py)
- Migration 130: `client_id` correct, RLS enabled
- 498 tests green post-merge

**Moratorium note:** True pending ≈ 4 (per run 28 governance audit). Exit threshold ≤ 2. PR #188 is first real production feature in 24 days — breaks the silence but doesn't reduce pending count.

---

## 5 Candidate Ideas

### Idea 1: Create post-split-test-repair SKILL.md (run 36 winner, 2nd recommendation)
**Evidence:** `5f2cd2b` (21 stale patches, 2026-05-22), `4afb3cf` (stale import, 2026-05-22), `bca2082` (2 stale filter mocks, 2026-05-28). Three test-repair commits in 6 days. `bca2082` broadens the scope beyond god-class splits — also fires after API cleanup migrations. Nightly review today did NOT implement from run 36 winning-concept.
**Action:** Create `.claude/skills/post-split-test-repair/SKILL.md` with the full 8-step checklist from run 36 winning-concept.md. Update title to "Test Mock Repair After Refactor" to cover broader pattern.
**Impact:** 15-20 min saved per refactor × 54+ remaining god-class targets + any future API migrations. email_sequences split (run 35) will need this immediately.
**Category:** workflow

### Idea 2: Billing-constant-guard pre-commit Check 11 (WARNING mode)
**Evidence:** GH #181 open 26+ days. Direct inspection of `billing.py` confirms `AMOUNT_TO_PLAN` at line 263 missing `15000` and `25000`. `test_billing_amount_to_plan.py:38-44` actively certifies the gap as correct. Parking-lot entry, ROI 2.1. Pattern: Check 5 (migration duplicate) was implemented as WARNING — same category of "persistent visibility guard."
**Action:** Add 10-line bash block to `scripts/hooks/pre-commit` as Check 11. Validate `AMOUNT_TO_PLAN` in `billing.py` contains `{9900, 15000, 25000, 89900}`. WARNING not FAIL (no dev-blocking dependency on GH #181 fix).
**Impact:** Makes billing gap visible on every commit. Prevents future billing constant drift (new plans, price changes). Creates systemic guard that survives GH #181 fix and beyond. Autonomously executable by nightly review.
**Category:** code_health

### Idea 3: Agent OS outbound delivery failure tracking
**Evidence:** PR #188 added 3 new external-API channels (Twilio SMS, Resend email, Facebook Graph API) sending messages to real customers. `os_outbound_log` table (migration 130) exists for replay protection. No `delivery_failed` column or alerting visible. `bca2082` was a post-merge test fix — suggests the new surface is still stabilizing.
**Action:** Add `delivery_failed BOOLEAN DEFAULT FALSE NOT NULL` to `os_outbound_log` (migration 131) + add log-level error in `os_outbound_mirror.py` when channel send fails, stored in the new column.
**Impact:** First monitoring on Agent OS outbound channels. Prevents silent dropped messages to customers — critical for Agent OS commercial value.
**Category:** operational

### Idea 4: Wire check_project_invariants.py into pre-commit as Check 10 (moratorium Item A)
**Evidence:** `check_project_invariants.py` PASSES all 6 checks (verified run 14+). Item A from moratorium sprint. Pre-commit has 9 checks, Check 10 slot open. 3-line addition to `scripts/hooks/pre-commit`. Run 8 winner (22+ days stale). Subsumed in sprint — but sprint not executed.
**Action:** Add 3 lines to `scripts/hooks/pre-commit` invoking `python3 scripts/check_project_invariants.py`. Exits non-zero on naming violations (client_id, status, areas_of_interest).
**Impact:** Enforces CLAUDE.md critical invariants #1-3 at commit time. 5-minute effort. Reduces class of production bugs from schema naming drift.
**Category:** code_health

### Idea 5: email_sequences.py god-class split via /god-class-splitter (run 35 winner)
**Evidence:** 1255L confirmed at `backend/routers/email_sequences.py`. 3 independent concerns (CRUD/enrollment/processor). GH #112/#113 N+1 easier post-split. Agent OS email outbound mirror (`email_sender.py` modified in PR #188) now interacts with email infrastructure — email_sequences.py quality matters more.
**Action:** Invoke `/god-class-splitter email_sequences.py` after GH #181 fix (~2h human session).
**Impact:** Smaller modules, N+1 fixes become trivial, safer Agent OS email integration. god-class-splitter skill ready (e848b87).
**Category:** code_health

---

## Ranking by Expected Impact (pre-debate)

1. **Idea 2** — Billing-constant-guard Check 11: ROI 2.1, autonomous, systemic guard, 26-day gap finally gets persistent CI visibility
2. **Idea 1** — post-split-test-repair SKILL.md: 3 occurrences, broadened scope, email_sequences split needs it
3. **Idea 3** — Agent OS delivery monitoring: high production impact but M-effort migration, moratorium timing risk
4. **Idea 4** — Check 10 (check_project_invariants): 5 min, valid, but standing sprint action (not novel)
5. **Idea 5** — email_sequences split: valid, run 35 winner stands, 2h human effort
