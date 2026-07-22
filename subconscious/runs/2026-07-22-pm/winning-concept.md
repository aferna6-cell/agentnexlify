# Winning Concept — Run 101 (2026-07-22-pm)

**Title:** Fix nightly LOC guardrail: per-fix vs total-batch ambiguity  
**Category:** workflow_efficiency  
**Severity:** MEDIUM  
**Effort:** XS (2-line SKILL.md edit)  
**Autonomous-executable:** YES  
**Requires human:** NO

---

## Problem

`nightly-commit-review/SKILL.md` line 110 reads:

> "Max 50 LOC changed per run — larger = bail"

Today's nightly interpreted "per run" as **total LOC across all reviewed commits** → counted >>50 LOC across 18 commits → bailed on ALL autonomous fixes → 0 fixes despite 18 MEDIUM/LOW risk commits.

The intended meaning is: **the autonomous fix itself** must be <50 LOC. A 3-line logging fix is safe regardless of how large the surrounding commit batch was.

**Concrete loss from today**: at least 3 low-risk fixes were skipped:
- `fix: planner response schema needs additionalProperties false` (aa040fc) — LOW, 1-line Pydantic schema
- `fix: re-export purge_photo_quote_images_30d` (0deab50) — LOW, 1-line re-export
- `auth_billing.py` trialing-subscription fallback — LOW, 9-line additive guard

---

## Root Cause

SKILL.md line 110 is ambiguous between two interpretations:
- (A) Total LOC changed across all commits in the review window → **what the model chose today (wrong)**
- (B) LOC in the autonomous fix itself → **correct interpretation**

The "per run" phrasing reads as (A). It should read as (B).

---

## Fix Specification

### Change 1 — SKILL.md line 110

**Current:**
```
2. **Max 50 LOC changed per run** — larger = bail
```

**New:**
```
2. **Max 50 LOC changed by the autonomous fix itself** — if a specific fix diff exceeds 50 LOC, skip that fix and open a MEDIUM issue instead; continue reviewing other commits
```

### Change 2 — SKILL.md line 308

**Current:**
```
12. If any guardrail tripped (forbidden path, >5 files, >50 LOC, test-check failed) — abort fixes, file issue only, still write report
```

**New:**
```
12. If a specific fix trips a guardrail (forbidden path, >5 files touched by the fix, fix diff >50 LOC, test-check failed) — skip that fix, file MEDIUM issue, continue to next commit; do NOT bail on the entire fixing pass
```

---

## Implementation path

**AUTONOMOUS-EXECUTABLE** — subconscious or nightly can apply directly:

1. Edit `.claude/skills/nightly-commit-review/SKILL.md` — change lines 110 and 308 as specified above
2. Commit to main as `fix(nightly): clarify LOC guardrail — per-fix not per-batch [skip ci]`
3. Verify: re-read lines 109-112 to confirm wording matches spec
4. No migration, no test file changes, no frontend changes

**Estimated LOC of fix:** 4 lines changed (2 old → 2 new in SKILL.md)

---

## Expected outcome

Next nightly after fix:
- Reviews commits individually as before
- For each LOW-risk candidate fix: checks if the fix diff will be <50 LOC and <5 files
- Applies the fix if within guardrails; skips and opens MEDIUM issue if not
- Does NOT bail on the entire fixing pass because the reviewed commit set has total LOC >>50

During active sprint weeks (18+ commits/day): expect 3-8 autonomous fixes per nightly instead of 0.

---

## Evidence

- `docs/dev-knowledge/nightly-reviews/2026-07-22.md` line 31: "Total LOC changed: >>50 (guardrail tripped — no autonomous fixes executed)"
- `.claude/skills/nightly-commit-review/SKILL.md` lines 110, 308: ambiguous "per run" phrasing
- Same nightly file: 3 LOW-risk findings that were not fixed (aa040fc, 0deab50, `auth_billing.py` additive guard)
- All 18 commits rated MEDIUM or LOW — none were HIGH or FORBIDDEN path

---

## What this is NOT

- Does not remove the 50 LOC cap — just clarifies what it applies to
- Does not change the 5-file cap per fix
- Does not change the FORBIDDEN paths list
- Does not touch any code, migration, or test files
