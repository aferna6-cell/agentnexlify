# Nightly Commit Review — 2026-05-29

**Window:** last 24h  
**Commits reviewed:** 3  
**LOW fixes applied:** 1  
**MEDIUM/HIGH issues filed:** 0 (GH #181 already open)

---

## Commits Reviewed

### 1. `3af4626` — subconscious: run 2026-05-28-pm (Run 38)
**Risk:** LOW  
**Files:** `subconscious/runs/2026-05-28-pm/` (5 files), `subconscious/state/governance.json`, `subconscious/state/memory.jsonl`  
**Content:** Strategic planning output. AI-to-Human Handoff v1 chosen as run 38 winner. Recommends trigger detection in `widget_chat.py` + `handoff_requests` migration + `handoff_service.py` + notification via `os_outbound_mirror`. MEDIUM confidence. No code changes.  
**Issues found:** None. Planning docs only.

### 2. `033fc3b` — subconscious: run 2026-05-28 (Run 37)
**Risk:** LOW  
**Files:** `subconscious/runs/2026-05-28/` (5 files), `subconscious/state/governance.json`, `subconscious/state/memory.jsonl`  
**Content:** Billing-constant-guard pre-commit Check 11 chosen as run 37 winner. HIGH confidence, flagged as autonomous-executable. No code changes — plan only.  
**Issues found:** Check 11 not yet implemented → fixed this session (see Fix Applied below).

### 3. `dc5ef8e` — ops: nightly-commit-review 2026-05-28
**Risk:** LOW  
**Files:** `ops/routines/logs/nightly-commit-review-2026-05-28.md`  
**Content:** Prior nightly log. No code changes.  
**Issues found:** None.

---

## Fix Applied (LOW risk)

### billing-constant-guard Check 11 added to `scripts/hooks/pre-commit`

**What:** 20-line bash block that runs on every commit. Checks `AMOUNT_TO_PLAN` in `backend/routers/billing.py` for four required current-price entries (`9900`, `15000`, `25000`, `89900`). Emits WARNING (non-blocking) on any missing entry.

**Why:** Recommended by subconscious runs 37 and 38 consecutively, both labeling it autonomous-executable. The guard addresses GH #181 symptom: `15000` (autopilot, $150/mo) and `25000` (professional, $250/mo) are missing from `AMOUNT_TO_PLAN`. Stripe webhooks for those plans fall through to `_resolve_plan`'s fallback and return `None`, silently misrouting plan assignment.

**Verification:** Ran `bash scripts/hooks/pre-commit` with file staged. Check 11 fired WARNING correctly:
```
Check 11: Billing constant guard... WARNING
  AMOUNT_TO_PLAN in backend/routers/billing.py missing entries: 15000 25000
  Expected: 9900 (growth), 15000 (autopilot), 25000 (professional), 89900 (enterprise)
  Fix: backend/routers/billing.py — see GH #181
1 warning(s) found. Committing anyway.
```
Other checks 1-9 all PASS. No regressions.

Verified: bash scripts/hooks/pre-commit — PASS (Check 11 fires WARNING as expected)

---

## Standing MEDIUM Issue (pre-existing, not filed tonight)

**GH #181** — `billing.py:265-279` `AMOUNT_TO_PLAN` missing `15000: "autopilot"` and `25000: "professional"`. Open 27 days. MEDIUM risk (billing logic, payments). Human approval required. Check 11 now surfaces this on every commit. No action taken beyond guard.

---

## Subconscious Run 38 Standing Actions (for human session)

In priority order per `subconscious/runs/2026-05-28-pm/improvement-backlog.md`:

1. **GH #181 billing fix (~15 min)** — `billing.py` add `15000: "autopilot"`, `25000: "professional"` to `AMOUNT_TO_PLAN`; remove backwards test assertions in `test_billing_amount_to_plan.py:38-44`. Human required.
2. **AI-to-Human Handoff v1 (~1 day)** — `widget_chat.py` trigger detection + `migrations/131_handoff_requests.sql` + `backend/services/handoff_service.py` + tests. MEDIUM confidence. Invoke `/new-feature` or `compound-engineering`.
3. **Invoke /moratorium-sprint (~40 min)** — Items A (check_project_invariants), B (widget sync guard), D (CI eval). 24+ days outstanding.
4. **email_sequences.py split (~2h)** — invoke `/god-class-splitter email_sequences.py`. After GH #181 fix.
5. **post-split-test-repair SKILL.md (~5 min)** — create `.claude/skills/post-split-test-repair/SKILL.md`.
