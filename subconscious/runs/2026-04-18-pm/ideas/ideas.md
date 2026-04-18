# Candidate Ideas — 2026-04-18-pm

Generated from: git log (3 days), audit-architecture-2026-04-18.md, bug-patterns.md, daily-logs/2026-04-17.md, customer-gaps.md, governance.json parking lot.

---

## Evidence Digest (200w)

**50 commits in 3 days.** Major feature: business-type personalization (20 files). Launch risk guardrails landed. Architecture audit (2026-04-18) found 4 HIGH god classes (SettingsPage 2,262 LOC; ConversationsPage 2,039; LeadDetailDrawer 1,688; widget_helpers.py 1,635) plus migration numbering collision (005, 007 duplicates). `widget_helpers.py` REGRESSED from 1,632 → 1,635 lines in 48 hours. Bug-patterns.md shows two spec-drift bugs landed 2026-04-15 (ExtractorError vs ValueError; session_id dedup). Daily log Apr 17 flagged: `silent_frontend_catch_count` reported 0 in morning, 9 in evening — same script, different glob expansion — monitoring reliability broken. Deep-research spike on TCPA/state AI laws committed 2026-04-17. No new production QA on 2 large structural refactors (auth, scheduled_jobs) that landed same day. Active direction (JS Silent Catch guard, run 3) still pending approval.

---

### Idea 1: Fix Health-Check Script Morning Grep Drift
**Evidence:** Daily log 2026-04-17 self-improvement section: "Fix `scripts/daily/health-check.sh` to use explicit glob expansion or `find`." `silent_frontend_catch_count` reported 0 at morning, 9 at evening — same script invoked differently. If the monitoring that drives this subconscious loop is unreliable, every downstream decision is suspect.
**Action:** Edit `scripts/daily/health-check.sh` — replace shell glob pattern for JS catch scan with `find frontend/src -name "*.jsx" -o -name "*.js" | xargs grep -lE "\.catch\s*\(\s*\(\s*\)\s*=>"` to ensure consistent results regardless of shell invocation context.
**Impact:** Reliable health metrics → monitoring trustworthiness restored → fewer false-negative alerts → subconscious evidence quality improves.
**Category:** operational

---

### Idea 2: Pre-commit Migration Number Collision Guard
**Evidence:** audit-architecture-2026-04-18.md HIGH item: "Migration 005/007 duplicate numbering — Fix: Enforce strict sequential check in `scripts/hooks/pre-commit` for numbers ≥106." Current hook has 7 checks but none verify migration sequence. Two historical duplicates (005, 007) exist and can't be renumbered; future ones can be blocked.
**Action:** Add Check 9 to `scripts/hooks/pre-commit`: when a new `migrations/NNN_name.sql` is staged, verify NNN is not already present in `migrations/`. Emit BLOCK (not warning) since duplicate migrations cause silent Supabase replay failures.
**Impact:** Prevents migration collision bugs — among the hardest schema bugs to diagnose in production. One grep, zero dependencies.
**Category:** code_health

---

### Idea 3: Split `widget_helpers.py` into Three Service Modules
**Evidence:** Parking lot item ROI 2.1 (highest in parking lot, note: "widget_helpers.py changed 8x/7 days, 3 bugs there"). audit-architecture-2026-04-18.md HIGH: 1,635 lines, REGRESSED from 1,632 in 48h, "blocking widget iteration per prior audit." Four callers identified: `widget_chat.py:26`, `widget_lead.py:20`, `widget_config.py:23`, `twilio_webhooks.py:238`. Audit gives concrete split plan.
**Action:** Split `backend/routers/widget_helpers.py` → `widget_chat_helpers.py` (prompt + history assembly), `widget_lead_helpers.py` (lead capture + enrichment), `widget_booking_helpers.py` (booking prep + callback logging). Update 4 caller imports. Branding filters stay in `widget_helpers.py` as shell if needed.
**Impact:** Reduces blast radius on hottest backend file. Unblocks Widget Hot-Zone Regression Suite (parking lot). Enables parallel widget feature development without merge conflicts.
**Category:** code_health

---

### Idea 4: Split `SettingsPage.jsx` into Tab-Panel Components
**Evidence:** audit-architecture-2026-04-18.md HIGH #1, Effort: L, recommended as sprint execution order #1: "user-facing blast radius, touched often." 2,262 lines — 3rd largest file in repo after widget JS bundles. 7+ concerns mixed (profile, widget config, branding, billing, integrations, team, notifications, API keys).
**Action:** Create `frontend/src/pages/Settings/` with `ProfilePanel.jsx`, `WidgetPanel.jsx`, `BrandingPanel.jsx`, `BillingPanel.jsx`, `IntegrationsPanel.jsx`, `TeamPanel.jsx`. Parent `SettingsPage.jsx` ≤200 lines as shell + tab router.
**Impact:** Reduces cognitive load, enables tab-level feature isolation, lowers regression risk when settings features ship.
**Category:** code_health

---

### Idea 5: TCPA/State AI Law Compliance Checklist for Widget Outreach
**Evidence:** research-skill-graph/research-queue commit `89617d7` (2026-04-17) produced a 294-line deep-dive on TCPA/state AI laws/CAN-SPAM risks. Widget sends SMS (Twilio), automated follow-ups, AI-generated messages — all regulated surfaces. No compliance checklist exists in the repo. One KB article (`ftc-auto-dealers-deceptive-pricing-2026.md`) exists on FTC but nothing on TCPA + widget specifically.
**Action:** Produce `docs/ops/tcpa-compliance-checklist.md` — surface-by-surface (SMS, email, AI disclosure, chat widget) with opt-in requirements, consent capture points in widget flow, and action items for onboarding UI.
**Impact:** Reduces regulatory exposure for AgentNexLiFy and tenants. Competitive signal (few $200/mo SMB tools document TCPA posture). Grounds future consent-capture feature work.
**Category:** operational / customer_value
