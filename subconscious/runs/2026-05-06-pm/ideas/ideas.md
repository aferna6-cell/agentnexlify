# Ideas — Run 15 (2026-05-06-pm)

## Evidence Digest (200 words)

7 commits in 3 days — light KB maintenance activity. No sprint active.

Critical findings:
1. **Run 14 winner unimplemented (1 day):** `.github/workflows/lead-qualifier-eval.yml` absent. Pre-commit Check 10 (check_project_invariants bonus) also missing — hook only runs through Check 9.
2. **Queue at 4 pending** (runs 4, 7, 8, 14) — exceeds moratorium threshold of 3. Moratorium re-triggered.
3. **Run 4 (AI handoff) 20+ days** — exceeds max_pending_age_days of 14.
4. **Widget 3-Copy Sync Guard script MISSING** (run 7, 12 days pending). `scripts/check-widget-sync.sh` never created.
5. **check_project_invariants.py PASSES** all 6 checks — wire is zero-risk.
6. **Architecture audit (2026-05-02):** 10 god classes CRITICAL (>1000 LOC). N+1 loops in `leads.py:714,866` and `onboarding.py:486`. `time.sleep` in async path at `llm_runtime.py:316`.
7. **Zapier auth bypass (Issue #107):** bug-patterns.md references `backend/services/zapier_auth.py` — file not found at this path. Path needs verification before any fix.
8. **Nightly review fired** (e9c100e, 2026-05-06 06:40 UTC) — content inaccessible; no LOW fixes auto-applied.

---

## Idea 1: Wire check_project_invariants.py into pre-commit (run 8 close)

**Evidence:** Run 14 bonus step unimplemented. `scripts/hooks/pre-commit` has Check 9 as last check. No Check 10. `check_project_invariants.py` passes all 6 invariants (client_id, status, areas_of_interest, widget sync, em-dash, SDK wrapper). 11 days pending. Closing run 8 drops pending queue 4→3, lifts moratorium.

**Action:** Add 10-line bash block to `scripts/hooks/pre-commit` after Check 9 (~line 244). Sets Check 10. Calls `python3 scripts/check_project_invariants.py` and increments ERRORS on fail.

**Impact:** Guards against #1 most-common production bug class (column naming violations). Closes run 8. Pending 4→3 (moratorium threshold relief). S-effort, 5 minutes.

**Category:** code_health

---

## Idea 2: Fix Zapier plan_status auth bypass (Issue #107)

**Evidence:** bug-patterns.md (2026-04-30): `_get_api_key_client` resolves API keys without checking `plan_status`. Cancelled tenants with un-revoked keys can auth Zapier endpoints. Issue #107 filed, no fix. NOTE: `backend/services/zapier_auth.py` NOT found at stated path — path needs verification before remediation.

**Action:** Locate actual Zapier auth file (grep for `_get_api_key_client`). Add `.in_("plan_status", ["active", "trialing"])` to Supabase query. Add regression test: seed cancelled tenant + valid key, assert 402/403. Fix Issue #107.

**Impact:** Closes security gap — revenue leak + compliance risk. S-effort (1-2 hours including test). Does NOT add to pending approval queue (security bug fix, not structural improvement).

**Category:** code_health / security

---

## Idea 3: Widget 3-Copy Sync Guard (run 7 close)

**Evidence:** Run 7 winner (2026-04-24, 12 days pending). `scripts/check-widget-sync.sh` never created. 3 widget copies confirmed: `widget/`, `frontend/public/widget/`, `landing-page-v2/widget/`. CLAUDE.md Invariant #4 says "2 copies" but reality is 3.

**Action:** Create `scripts/check-widget-sync.sh`: sha256sum all 3 copies, fail if any hash differs. Wire into `scripts/hooks/pre-push`. Update CLAUDE.md Invariant #4 ("2 → 3 widget paths").

**Impact:** Prevents widget drift bugs on tenant embeds. S-effort (30 min). Closes run 7. Pending 4→3 (moratorium threshold relief, same as run 8).

**Category:** code_health

---

## Idea 4: Implement AI-to-Human Handoff v1 (run 4, moratorium oldest)

**Evidence:** run 4 (2026-04-16, 20+ days pending). Exceeds max_pending_age_days of 14. customer-gaps.md: Critical cross-industry rating, all 7 industries. Infrastructure exists (conversations table, webhooks, Twilio, Resend). No new evidence since run 4.

**Action:** Implement explicit-trigger-only v1: widget surfaces "Talk to a human" trigger phrase → flag conversation → notify tenant via Twilio SMS + Resend email with lead context.

**Impact:** Critical customer gap closed. All 7 industry verticals benefit. M-effort (1.5-2 days).

**Category:** customer_value

---

## Idea 5: Fix N+1 in leads.py (Architecture Audit)

**Evidence:** audit-architecture-2026-05-02.md: `backend/routers/leads.py:714,866` — per-lead update inside loop. File is 1158 lines (confirmed). Batch via RPC or `.upsert()`. Also `onboarding.py:486` insert loop. Both rated HIGH in audit.

**Action:** Replace loop at `leads.py:714,866` with batch `.upsert()` call. Add characterization test for bulk lead update. Fix `onboarding.py:486` insert loop similarly.

**Impact:** Performance at scale (today 100s of leads, tomorrow 1000s). Prevents timeout bugs during bulk operations. M-effort.

**Category:** code_health / operational
