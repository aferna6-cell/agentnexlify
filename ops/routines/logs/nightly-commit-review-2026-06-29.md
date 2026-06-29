# Nightly Commit Review — 2026-06-29

**Run time:** 2026-06-29 (UTC)  
**Commits reviewed:** 1 (last 24h)  
**Issues found:** 1  
**Fixes applied:** 0  
**GitHub issues created:** 1

---

## Commits Reviewed

### 86890cb — subconscious: run 2026-06-28-pm — SMS Compliance Dashboard

**Risk:** LOW  
**Files:** 12 (all docs/state — subconscious/runs/*, subconscious/state/*, docs/reminders/)  
**Code changes:** None — planning artifacts only

Summary of contents:
- `docs/reminders/widget-drift-URGENT.md` — urgent reminder for human re: widget drift (see issue below)
- `subconscious/runs/2026-06-28-pm/` — run 70 artifacts: debate log, 5 ideas, winning concept, improvement backlog
- `subconscious/state/governance.json` — widget drift topic retired from subconscious (run_70_mandate executed)
- `subconscious/state/memory.jsonl` — state update

**Verdict:** No bugs. No action required. Commit is clean documentation/planning output.

---

## Issues Found

### [MEDIUM] Widget drift: landing-page-v2 out of sync

**File:** `landing-page-v2/widget/agentnexlify-widget.js`  
**Invariant:** `scripts/check_project_invariants.py` → FAIL (6th consecutive run)  
**Duration:** Since 2026-06-23 (5+ days)

**What changed:** `widget/agentnexlify-widget.js` gained referral click tracking (UTM link params + fire-and-forget POST to `/api/v1/referral/click`). Synced to `frontend/public/widget/` ✅. NOT synced to `landing-page-v2/widget/` ❌.

**Why not auto-fixed:** `landing-page-v2/` is on FORBIDDEN paths for all autonomous systems (CLAUDE.md: "legacy, do not touch"). Human action required.

**Fix:**
```bash
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
python3 scripts/check_project_invariants.py
git add landing-page-v2/widget/agentnexlify-widget.js
git commit -m "fix: sync widget to landing-page-v2 (resolves invariant FAIL)"
```

**GitHub issue:** Created (see label `nightly-review`, `medium-risk`, `widget`)

---

## Invariant Check Results

```
PASS FastAPI router files avoid future annotations
PASS active backend code avoids retired live-schema fields
PASS retired plan names do not appear in plan-related code
FAIL widget assets are byte-identical across mirrors
  - drift: widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js
PASS website source avoids em dashes
PASS direct Anthropic SDK message creation stays behind the runtime wrapper
1 invariant(s) failed.
```

---

## Subconscious Backlog (FYI, not code issues)

From run 70 improvement-backlog.md — items queued for future runs:

1. **KB autopopulate fix** (run 71) — broken 53 days, unknown root cause
2. **AI-to-Human Handoff v1** (runs 71-72) — 74 days pending, M-effort
3. **Record Audit Dashboard** (run 72) — `record_audit.py` exists, no operator UI
4. **Email sequences split** — `email_sequences.py` at 1143 lines, post-moratorium

These are not bugs. Listed for awareness only.

---

## Summary

1 commit reviewed, LOW risk (pure docs/state). No code bugs found. 1 MEDIUM issue escalated: widget drift in `landing-page-v2/` has been blocking `check_project_invariants.py` for 5 days — requires a single `cp` command by a human (30-second fix). GitHub issue filed.
