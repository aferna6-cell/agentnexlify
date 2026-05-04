# Candidate Ideas — 2026-05-04 (Run 13)

## Evidence Digest

1. **Repo idle since 2026-05-02** — no commits 48h. Nightly review 2026-05-04 confirmed zero activity. Last meaningful code commit: `b4b7c10` (email_sequences docstring + 409 fix, 2026-05-02).
2. **Moratorium still active** — 4 pending approvals (runs 3/4/7/8). Oldest: JS Silent Catch Guard, day 24+. AdminAnalyticsPage.jsx:117-122 still has 6 `.catch(() => null)` (confirmed live). Pre-commit has no Check 10.
3. **Email sequences N+1 opened** — GH #112 (list_enrollments: 1001 queries per 1000 enrollments) + #113 (process_sequences/run_sequence_processor ~120-line duplication). Both opened 2026-05-02 from nightly review of `fa466ca`.
4. **California AI companion law** — KB now has two articles (joneswalker-sb-243-companion-ai-mandate, perkinscoie-ca-companion-chatbot-law-now-effect). SB 243 in effect. May require disclosure in widget chat.
5. **Em-dash blocker unresolved** — check_project_invariants.py fails on 9 JSX em-dash violations. Blocks run 8 (wire invariants into pre-commit). Fix = one line (skip .jsx/.tsx in em-dash check).

---

### Idea 1: JS Silent Catch Guard — Fix AdminAnalyticsPage.jsx + Add Check 10 to pre-commit
**Evidence:** 10 consecutive runs (3, 9, 10, 11, 12) recommend this. AdminAnalyticsPage.jsx:117-122 confirmed 6 `.catch(() => null)` (live check 2026-05-04). Pre-commit has 9 checks, no Check 10. Run 12 winning-concept.md has copy-paste-ready implementation. Moratorium mandates recommendation until implemented.
**Action:** (1) Fix AdminAnalyticsPage.jsx:117-122 — add `console.warn` to 6 silent catches. (2) Add Check 10 bash block to scripts/hooks/pre-commit after Check 9. (3) Verify guard blocks staged `.catch(() => null)`. (4) Close Issue #109.
**Impact:** Lifts moratorium (4 → 3 pending), unblocks future runs. Prevents silent catch class from recurring in Onboarding V2 sprint JSX files. S-effort (30-min task, copy-paste-ready implementation sketch exists).
**Category:** code_health

---

### Idea 2: Fix email_sequences.py N+1 Queries (GH Issue #112)
**Evidence:** `fa466ca` (2026-05-01) shipped list_enrollments (lines 708–724) with 1 DB call per enrollment — 1000 enrollments = 1001 queries per request. list_sequences (lines 256–283) does 2 DB calls per sequence. GH #112 opened by nightly review 2026-05-02. Email automation is a new and growing feature; fix before scale, not after.
**Action:** Bulk list_enrollments via `.in_()` lookup on lead IDs in single query + Python dict join. Replace list_sequences double-per-row calls with group-by aggregation in single RPC or SELECT with JOIN.
**Impact:** 1000x DB query reduction on busy tenants. Prevents DB saturation once email automation reaches tenant scale (any tenant with 100+ enrollments hits this immediately).
**Category:** code_health / operational

---

### Idea 3: Scope em-dash Check in check_project_invariants.py to Skip .jsx/.tsx (Unblock Run 8)
**Evidence:** Run 8 winner ("Wire check_project_invariants.py into pre-commit") blocked since 2026-04-25 by em-dash false positives on JSX UI chars (`|| '—'` for empty table cells). 9 violations: WizardStepAutoKB.jsx:2/140/172/254 + AutomationActivityCard.jsx:156/172/188/251/389. Run 12 noted fix path: "one-line change in check_project_invariants.py — scope em-dash check to skip .jsx/.tsx files." Fixes the prerequisite, not the main item.
**Action:** In `scripts/check_project_invariants.py`, in the em-dash check loop, add `if path.endswith(('.jsx', '.tsx')): continue`. Rerun script to confirm 0 violations. Run 8 implementation then becomes unblocked.
**Impact:** Unblocks run 8 (High-confidence pending approval). Check_project_invariants prevents client_id/status/areas_of_interest naming bugs from shipping — the #1 schema discipline failure mode per CLAUDE.md.
**Category:** code_health / workflow

---

### Idea 4: Wire Golden Eval Harness to Weekly CI (GH Issue #110)
**Evidence:** backend/tests/evals/test_lead_qualifier_golden.py + lead_qualifier_golden.json added in 7854ede. Env-var gated, 80% pass threshold. GH #110 opened by nightly review 2026-05-01. Parking lot ROI 2.5 (highest in backlog). Parking lot note: "Promote as run 12 winner once moratorium lifts."
**Action:** Add .github/workflows/lead-qualifier-eval.yml with Monday cron. Set LEAD_QUALIFIER_AGENT_ID in GH Secrets. Wire eval to pass/fail CI gate.
**Impact:** Weekly automated regression signal on lead qualifier AI agent quality. Catches LLM output drift before customers notice. Only automated AI-output quality check in the system.
**Category:** agent_performance / operational

---

### Idea 5: Extract _process_pending_sends() from email_sequences.py (GH Issue #113)
**Evidence:** process_sequences (HTTP, lines 805–975) and run_sequence_processor (standalone, lines 997–1102) share ~120 lines of near-identical per-send loop logic. GH #113 opened by nightly review 2026-05-02. Docstring + 409 fix in b4b7c10 only applied to one path — duplication was already costing bug-fix overhead on day 1 of the fix.
**Action:** Extract private `_process_pending_sends(client_id, sequences)` helper. Both process_sequences and run_sequence_processor call it. Write one test per public path to confirm behavior unchanged.
**Impact:** Any future bug fix or enhancement applies once. Removes dual-application maintenance tax. M-effort.
**Category:** code_health
