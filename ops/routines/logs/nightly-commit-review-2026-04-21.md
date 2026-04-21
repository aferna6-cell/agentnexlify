# Nightly Commit Review — 2026-04-21

**Window:** last 24 hours from ~2026-04-21 00:00 UTC  
**Commits reviewed:** 33  
**LOW fixes applied:** 1  
**MEDIUM/HIGH issues opened:** 0  

---

## Triage Summary

### LOW (docs, renames, obvious fixes — no action)

| SHA | Description |
|-----|-------------|
| 62c21b7 | kb(log): append run summary |
| b5fd63a | KB articles: competitors/regulations |
| 00c8e5b | known-urls.json update |
| 4fedca0 | KB raw articles (4 articles) |
| 1ee1406 | docs(audit): health check findings |
| f8ba053 | advisor_executor prompt style flip (negatives → positive examples) |
| 8328e03 | opus-4-7-prompting rules sweep (6 files) |
| a955d75 | opus-4-7-prompting moves: agents + skills |
| bb857d9 | opus-4-7-prompting rules + CLAUDE.md update |
| aac598e | docs: auto-log bug fix |
| 611c052 | fix(hooks): skip frontend build when no frontend files changed |
| f05b2f4 | docs: auto-log bug fix |
| 0632799 | fix(automation): soften classifier prompt |
| 7179c85 | chore(ai): classify_issue.py + issue-to-pr.sh |
| 4f465df | chore(ai): issue-to-pr.sh improvements |
| 46656a5 | docs: auto-log bug fix |
| 4d2b4be | fix(automation): any() not inside() for label filter |
| 07a2bca | research: churn data |
| 97232aa | docs: auto-log bug fix |
| be135eb | fix(automation): source .env in cron scripts |
| 0e8d065 | feat(specs): drive-kb + zapier specs |
| e8d514c | chore(ai): nightly-commit-review.sh |
| 123f688 | docs: automated morning startup |
| 2a08588 | subconscious run |
| fa768c6 | kb(log) |
| 47726aa | KB articles (4 articles) |
| f81dcd1 | KB articles + architecture audit |
| cf0d9ae | research: SMB segment |

### MEDIUM (reviewed — no issues found)

| SHA | Description | Finding |
|-----|-------------|---------|
| 670b1b3 | Launch readiness + contractor pack | `branding_service.seed_industry_faqs` mapping fixed (home_services→home_services FAQs, not plumbing). `CONTRACTOR_VERTICAL_PACK` all fields present. `from __future__` in `mtoptions_phase5_measurement.py` is a standalone script, not a FastAPI file — rule does not apply. Tests: all assertions satisfiable (7 kb_seed_articles ≥ 7). CLEAN. |
| 488eb63 | Migrations 109+110 | `client_id` used (not `tenant_id`) ✓. RLS enabled on all tables ✓. Applied via Supabase MCP, verified in commit msg. `key_hash text not null` correct for bcrypt. CLEAN. |
| d818462 | Migration 108 photo-quote | `client_id` ✓, RLS ✓, `security definer` on purge function appropriate (cross-tenant maintenance). CLEAN. |
| 15fc856 | Agent reliability checks | Pre-push now calls `check:quick`. No recursion (check:quick is read-only Python scripts). Package.json scripts verified against expected strings. CLEAN. |
| e6cbd45 | Agent reliability command layer | `check_project_invariants.py` added, guards `leads.tenant_id`. See fix below. |

---

## LOW Bug Fixed

### `check_project_invariants.py` missing `conversations.tenant_id` guard

**File:** `scripts/check_project_invariants.py:244`  
**Commit introducing it:** e6cbd45  
**Issue:** Script checks `leads.tenant_id` (CLAUDE.md Rule 1) but not `conversations.tenant_id`. Rule 1 explicitly covers **both** `leads` + `conversations` tables.  
**Fix applied:** Added `conversations.tenant_id` check at line 246.  
**Risk:** LOW — additive check in a read-only static analysis script, no logic change.

```diff
+            if "conversations.tenant_id" in line:
+                issues.append(f"{rel(path)}:{lineno}: conversations.tenant_id")
+                continue
```

---

## No MEDIUM/HIGH Issues Found

All schema migrations use `client_id` correctly. All new tables have RLS enabled. No auth/payments/tenant-isolation code touched. No `from __future__ import annotations` in FastAPI router files.

---

Verified: diff shows only expected 3-line addition at scripts/check_project_invariants.py:246 — PASS
