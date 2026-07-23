# Ideas — Run 101 (2026-07-23-pm)

## Idea 1 — Step 9G: KB Autopopulate Self-Healing Trigger (CARRY-FORWARD)

**Category:** workflow_efficiency  
**Evidence:**
- Run 100 mandate: "check Step 9G in SKILL.md next run" — FAIL (grep returns 0 matches)
- nightly-2026-07-22 confirms Step 9F fires: "KB STALE (9 days) — comment added to GH #403"
- KB ran 2026-07-23 via MANUAL CCR session (log.md: "manual catch-up"), NOT via kb-autopopulate.yml
- Automated workflow still broken: ANTHROPIC_API_KEY not in GH Actions secrets (GH #403 open)
- KB embeddings still SKIPPED (no VOYAGE_API_KEY in GH Actions)
- Steps 9B-9F all implemented in 1 cycle each via SKILL.md bash block edits (proven channel)
- This is the 2nd carry-forward cycle; mandated by governance

**Action:** Add Step 9G bash block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9F block. Trigger `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`; sleep 30; check conclusion; if failed comment on GH #403 with specific diagnostic ("check ANTHROPIC_API_KEY + VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN in GH Actions Secrets"). ~30 lines.

**Impact:** HIGH — converts passive alert (Step 9F) to active self-healing. Catches the exact silent-failure class that caused the 63-day stale gap in early 2026.

---

## Idea 2 — Credential Tracking Gap: VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN

**Category:** operational  
**Evidence:**
- `ops/credential-rotation-schedule.md` tracks 2 credentials (AUTOPILOT_GH_TOKEN, Brain PAT)
- VOYAGE_API_KEY: not tracked, not in GH Actions secrets → KB embeddings always skipped
- SUPABASE_ACCESS_TOKEN: tracked as "unknown — not yet set" (Step 9E, 2026-07-22 review)
- Both are required for kb-autopopulate.yml to work end-to-end
- Step 9E only checks credentials already listed; missing entries never surface

**Action:** Add VOYAGE_API_KEY and SUPABASE_ACCESS_TOKEN entries to `ops/credential-rotation-schedule.md` with status "not_set — required for kb-autopopulate.yml". No code change, just ops doc update.

**Impact:** MEDIUM — makes the gap visible to Step 9E's automated check. Low effort.

---

## Idea 3 — SHOW_BOOKING_PANEL Funnel Completeness Check

**Category:** code_health  
**Evidence:**
- Commit e9b4972 (2026-07-23): 19 new lines added to `docs/dev-knowledge/bug-patterns.md` for SHOW_BOOKING_PANEL
- New file `backend/routers/widget_chat_booking_action.py` (33 lines): `detect_show_booking()` strips marker, returns `(clean_text, show_booking_flag)`
- Marker hallucinated on non-booking tenants is swallowed silently — but is the native booking panel wired end-to-end?
- No test coverage for the booking panel flow in recent commits
- Revenue-critical: booking is the primary conversion path for salon/service tenants

**Action:** Verify `widget_chat_booking_action.py` is registered in `main.py` routers AND that `show_booking_flag` is consumed by the frontend widget to actually show the booking panel. Confirm test exists for both the happy path and the non-booking-tenant case.

**Impact:** HIGH — silent failure here means bookings never trigger for tenants who need it. 19 bug-pattern lines is a yellow flag on a new file.

---

## Idea 4 — email_sequences.py Split Registration Verification

**Category:** code_health  
**Evidence:**
- Commit ab1a7c2: email_sequences.py split into email_crud.py (529L) + email_enrollment.py (328L) + email_processor.py (341L)
- Split eliminates the 1255-line god class (Rule 9 compliance)
- Risk: main.py router registrations must be updated to include the new modules
- Previous god-class splits (brain/ split, routers/ split) have required main.py registration fixes

**Action:** Grep `main.py` for email_crud, email_enrollment, email_processor imports and router registrations. If any missing, flag as issue.

**Impact:** MEDIUM — missing router registration = 404 on email sequence endpoints for all tenants.

---

## Idea 5 — Voice Workforce Bridge Monitoring Gap

**Category:** agent_performance  
**Evidence:**
- Commit 9166b64 (2026-07-22) includes "voice-workforce bridge" in summary
- No corresponding health check in nightly-commit-review Steps (9A-9F only)
- Voice path is a new integration surface (Twilio → AI workforce agent handoff)
- SUPABASE_ACCESS_TOKEN not set means brain connector "skipped" on supabase (Step 9C, 2026-07-22)

**Action:** No action this run — insufficient evidence of failure. Park for next cycle if voice errors appear in logs.

**Impact:** LOW — speculative, no failure evidence yet.
