# Nightly Commit Review — 2026-05-23

## Stats

- Commits reviewed: 17 (last 24h)
- LOW risk: 13
- MEDIUM risk: 4
- HIGH risk: 0
- Fixes applied: 1
- GH issues filed: 1

---

## Commit Triage

| SHA | Message | Risk | Finding |
|-----|---------|------|---------|
| 08649e1 | subconscious: run 2026-05-22-pm (run 30) | LOW | Docs only. Recommends billing constants tests. |
| 41b1952 | Finish OS plan, refactor codebase, remove non-Claude AI configs (#179) | LOW | Cleanup: removed aider/cursor/copilot/windsurf configs. No code risk. |
| 4fb23a5 | Ignore coverage artifacts | LOW | .gitignore only. |
| 1eaaeec | Fix billing AMOUNT_TO_PLAN, cover local SEO error paths, wire into CI | MEDIUM | Billing constants + new SEO error tests + CI wiring. No new bugs found in this commit. |
| 588450f | fix: strip trailing whitespace from automation log files | LOW | Formatting fix. Clean. |
| 5f2cd2b | test: repoint stale patch targets and imports after refactor | LOW | Tests updated to track refactored modules. Normal follow-up. |
| 4afb3cf | Fix test_local_seo_parsers import | LOW | One-line import fix. |
| c72b535 | Fix AMOUNT_TO_PLAN: correct $150/$250 plan mappings, add enterprise | MEDIUM | **Gap found**: removed wrong mappings (15000→professional, 25000→enterprise) but did NOT add correct ones (15000→autopilot, 25000→professional). See GH #181. |
| 3555645 | Split local_seo_handlers god class into execute + fetch modules | MEDIUM | Rule 9 applied correctly. Verified PASS by author (24 tests). Local_seo.py imports confirmed correct. |
| d8a89f3 | chore(ai): auto-commit — local_seo_fetch.py | MEDIUM | New service created. Imports from local_seo.py verified clean. |
| c63888f | Add staged god-class refactor plan | LOW | Plan doc only. |
| e0b3078 | Reorganize audit reports, add local_seo_execute.py | MEDIUM | New service + audit reorganization. No code risk from audit moves. |
| d4658fc | Remove dead artifacts | LOW | Dead test fixtures, stale plans. Clean removal. |
| eba5dd9 | Finish remaining OS plan items: skill effort frontmatter | LOW | Metadata only. |
| b1d550a | Remove non-Claude AI tool configs | LOW | Housekeeping. |
| ead3562 | ops: morning-digest 2026-05-22 | LOW | Ops log. |
| 1f8f871 | ops: nightly-commit-review 2026-05-22 | LOW | Ops log. |

---

## Fixes Applied

### LOW: Wire billing tests into CI

**File**: `.github/workflows/pr-check.yml` line 132

Added `backend/tests/test_billing_amount_to_plan.py` to the `pytest` invocation in CI. This file existed but wasn't being run in PR validation, meaning billing constant regressions would pass CI silently.

**Before**:
```
python -m pytest tests backend/tests/test_local_seo_handlers.py ...
```

**After**:
```
python -m pytest tests backend/tests/test_local_seo_handlers.py backend/tests/test_billing_amount_to_plan.py ...
```

Commit: applied to main directly (LOW risk, CI config only).

---

## GH Issues Filed

### MEDIUM: GH #181 — billing: AMOUNT_TO_PLAN missing current autopilot ($150) and professional ($250) entries

**Commit**: c72b535
**File**: `backend/routers/billing.py` line 263

c72b535 removed the wrong mappings `15000→professional` and `25000→enterprise` (correct) but did not add the correct mappings `15000→autopilot` and `25000→professional`. Customers on these current price points without `metadata.plan` will resolve to `None` in `_resolve_plan()`, potentially causing silent plan downgrades.

Labels: `nightly-review`, `medium-risk`, `billing`
https://github.com/aferna6-cell/agentnexlify/issues/181

---

## Notes

- Subconscious run 30 (08649e1) recommended creating `backend/tests/test_billing_constants.py`. The existing `test_billing_amount_to_plan.py` covers the same ground — wiring it into CI achieves the same safety goal. `PLAN_TO_STRIPE_PRICE` referenced in the subconscious sketch does not exist in billing.py; implementing the sketch verbatim would fail.
- Local SEO god-class split (3555645 + d8a89f3 + e0b3078) is complete per Rule 8. Original file deleted, single importer migrated, tests pass.
- No auth, payments (logic), or schema changes requiring immediate escalation beyond GH #181.
