# Winning Concept — Run 2026-09-12-pm (Run 122)

**Winner:** Step 9E — Countdown + credential-identity dedup fix
**Category:** workflow_efficiency / operational
**Effort:** XS
**Confidence:** HIGH
**Source:** Run 121 mandate item 4 + direct read of current Step 9E

---

## Problem

`.claude/skills/nightly-commit-review/SKILL.md` Step 9E currently uses the right 14-day warning threshold numerically but expresses it indirectly and has unsafe global dedup:

- `days_since_rotation >= 76` is equivalent to `90 - days_since_rotation <= 14` for the current 90-day interval. This is not an earlier-warning behavior change; it is a clarity/countdown change.
- The issue title says `≤14 days`, but the block never computes or displays `days_remaining`.
- Dedup searches only for any open issue with label `credential-rotation`, not for the specific credential identity. With multiple credentials, that can comment on the wrong tracker or suppress creation of a needed tracker.

**Current state (2026-09-12):**
- AUTOPILOT_GH_TOKEN: ~70d elapsed, next due ~2026-10-02 (20 days)
- Current warning threshold fires at 76d, around 2026-09-18, leaving ~14 days
- Existing tracker #399 should be reused for AUTOPILOT_GH_TOKEN rather than creating or commenting on an unrelated credential issue

---

## Proposed Change

Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E:

1. Compute `days_remaining = interval_days - days_since_rotation` and use `days_remaining <= 14` as the readable equivalent of the current 76-day warning threshold.
2. Include credential name plus `days_remaining` in the nightly log and GitHub comment.
3. Deduplicate by credential identity across open human-action/ops/credential-rotation trackers, reusing an existing matching tracker such as #399 for AUTOPILOT_GH_TOKEN. Do not treat any arbitrary open `credential-rotation` issue as a match.
4. Unknown or unset rotation dates remain a separate `unknown_state` path and must not be assigned a fabricated countdown.

---

## Impact

- Preserves the existing 14-day warning window while making the countdown explicit and auditable
- Prevents cross-credential issue dedup mistakes
- Reuses existing credential-specific trackers instead of creating duplicates
- Keeps unknown-date credentials honest rather than inventing expiry math

---

## Run 123 Mandate

1. Grep confirms `days_remaining` and `<= 14` in Step 9E block — PASS/FAIL
2. Verify Step 9E searches/reuses trackers by credential identity, not globally by `credential-rotation` label
3. Verify AUTOPILOT_GH_TOKEN reuses GH #399 and posts a countdown after implementation
4. Promote Step 9J (limit=5) to winner if Step 9E confirmed implemented
5. Check if tool outcome coverage GH issue was filed opportunistically
