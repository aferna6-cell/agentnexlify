# Winning Concept — Run 2026-09-12-pm (Run 122)

**Winner:** Step 9E — Threshold Consistency Fix + days_remaining Display  
**Category:** workflow_efficiency / operational  
**Effort:** XS  
**Confidence:** HIGH  
**Source:** Run 121 mandate item 4 + SKILL.md inconsistency (line 289 vs line 294)

---

## Problem

`.claude/skills/nightly-commit-review/SKILL.md` Step 9E block has inconsistent threshold logic:

- **Line 289:** `if any credential approaching expiry (days_since_rotation >= 76)` — fires at 76 days elapsed
- **Line 294 (issue title):** `"Credential rotation due in ≤14 days: [credential name(s)]"` — says ≤14 days

The title claims "≤14 days" but the trigger doesn't compute `days_remaining` at all. There is no `days_remaining` variable anywhere in the Step 9E block. The GH issue filing and dedup logic (lines 290-299) were added in a prior run — that part works.

**Current state (2026-09-12):**
- AUTOPILOT_GH_TOKEN: ~70d elapsed, expires ~2026-10-02 (20 days)  
- Current trigger fires at 76d → ~2026-09-18 (6 days from now)
- At firing, `days_remaining ≈ 14` — buffer is fine but undisplayed
- Without `days_remaining` in the comment, humans don't see the countdown

---

## Proposed Change

Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block, line ~289:

### Change 1: Add days_remaining calculation
```
CURRENT (line 289):
  If any credential approaching expiry (days_since_rotation >= 76):

PROPOSED:
  days_remaining = interval_days - days_since_rotation
  If days_remaining <= 14:
```

### Change 2: Add days_remaining to log line (line ~300)
```
CURRENT log line:
  "Step 9E: {N} credentials checked, {M} approaching expiry (>=76 days), {K} unknown state"

PROPOSED log line:
  "Step 9E: {N} credentials checked, {M} approaching threshold ({days_remaining}d remaining), {K} unknown state"
```

### Change 3: Add days_remaining to GH comment body (line ~298)
In the `add_issue_comment` body, include: `"Days remaining: {days_remaining} (threshold: {interval_days - 76}d before {interval_days}d rotation interval)"`

---

## Impact

- Removes threshold inconsistency (trigger fires `days_remaining <= 14`, matches issue title "≤14 days")
- Humans see countdown in every GH comment and nightly log
- AUTOPILOT_GH_TOKEN expiry tracked visibly until rotated
- XS edit — 3 targeted changes within existing block

---

## Run 123 Mandate

1. Grep confirms `days_remaining` and `<= 14` in Step 9E block — PASS/FAIL
2. Verify AUTOPILOT_GH_TOKEN: GH #399 has a countdown comment from the nightly after implementation
3. Promote Step 9J (limit=5) to winner if Step 9E confirmed implemented
4. Check if tool outcome coverage GH issue was filed opportunistically
5. os_tool_executions.py line count: if ≥480L, consider Step 9M
