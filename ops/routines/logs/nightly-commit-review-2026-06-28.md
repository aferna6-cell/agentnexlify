# Nightly Commit Review — 2026-06-28

**Run date:** 2026-06-28 (UTC)
**Period:** last 24 hours
**Commits reviewed:** 2
**Issues found:** 0 new
**Issues created:** 0 (ongoing: #377)
**Fixes applied:** none needed

---

## Commits Triaged

### 1. `ffd9cdc` — subconscious: run 2026-06-27 — Hybrid Step 9B Widget Byte-Sync + Hard Run 70 Deadline
**Risk:** LOW
**Files:** 11 files in `subconscious/` (docs/planning only)
**Verdict:** Planning and governance artifacts. No code changed. No action.

### 2. `ffefe61` — fix: em-dash violations in JSX + widget comment (nightly-review 2026-06-27)
**Risk:** LOW (previously triaged and fixed by prior nightly run)
**Files:** 6 JSX files, widget mirrors (comment only), nightly log
**Verdict:** Em-dash replacements are cosmetic. Widget still byte-identical between `widget/` and `frontend/public/widget/` (verified). No logic changes. No bugs.

---

## Invariant Check Results

```
PASS FastAPI router files avoid future annotations
PASS active backend code avoids retired live-schema fields
PASS retired plan names do not appear in plan-related code
FAIL widget assets are byte-identical across mirrors
     drift: widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js
PASS website source avoids em dashes
PASS direct Anthropic SDK message creation stays behind the runtime wrapper
```

**1 failing invariant** — same as yesterday. No regression.

---

## Ongoing Issues

### Widget drift vs landing-page-v2 (MEDIUM) — GH issue #377
- `widget/agentnexlify-widget.js` has referral tracking code (UTM params + click listener) missing from `landing-page-v2/widget/agentnexlify-widget.js`
- `landing-page-v2/` is marked "legacy, do not touch (confirmed 2026-06-23)" in CLAUDE.md
- Fix is one `cp` command OR update invariant script to exclude legacy dir — requires human decision
- Issue #377 open, awaiting approval
- Subconscious run 69 notes: if invariant still fails at run 70, topic retires permanently

---

## New Issues Created

None. All findings already tracked.

---

## Summary

Clean run. No new bugs in either commit. Em-dash violation is fully resolved (PASS). Widget byte-identical between canonical mirrors. Only outstanding item is the `landing-page-v2/` drift in issue #377 (MEDIUM, awaiting human approval since 2026-06-23).
