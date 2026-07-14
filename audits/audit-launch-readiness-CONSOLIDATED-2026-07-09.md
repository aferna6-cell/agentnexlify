# Launch-Readiness Audit — Consolidated Report

**Date:** 2026-07-09
**Scope:** Full pre-launch audit across five dimensions — security, reliability/failure-handling, concurrency/state-integrity, accessibility (WCAG 2.2 AA), and UI consistency/responsive.
**Method:** Five parallel read-only auditor passes over the live source (`backend/`, `frontend/`, `widget/`, `migrations/`), each cross-checked against the production database and the byte-identical widget copies. Every headline finding re-verified by direct file read before inclusion. **No application code was modified during this audit.**
**Per-dimension detail (full findings, evidence, reproduction, fixes):**
- `audits/audit-security-launch-2026-07-09.md`
- `audits/audit-reliability-launch-2026-07-09.md`
- `audits/audit-concurrency-launch-2026-07-09.md`
- `audits/audit-accessibility-launch-2026-07-09.md`
- `audits/audit-ui-consistency-launch-2026-07-09.md`

---

## Findings tally

| Dimension | Blocker/Critical | High | Medium | Low | Info |
|---|---|---|---|---|---|
| Security | 0 | 1 | 1 | 3 | 3 |
| Reliability | 5 | 11 | 12 | 6 | — |
| Concurrency | 0 | 1 | 2 | 3 | 6 safe |
| Accessibility | 4 | 8 | 9 | 4 | — |
| UI consistency | 0 | 3 | 5 | 7 | — |
| **Total** | **9** | **24** | **29** | **23** | — |

The individual dimension reports give per-finding severity/category/location/issue/impact/evidence/reproduction/fix/confidence and mark Confirmed vs Needs-Verification. This consolidated report groups the launch-blocking and high tiers, then gives the remediation plan, quick-wins list, architectural list, and the ship verdict.

---

# LAUNCH BLOCKERS (must fix before shipping)

These are the findings that, unfixed, break the core product promise or leak customer data. Nine total — most are small, well-scoped fixes.

## Data loss / revenue path (Reliability)

- **C1 — Widget chat client timeout (15s) < server timeout (30s).** `widget/agentnexlify-widget.js:1057` aborts at 15s; `backend/routers/widget_chat.py:1029` runs to 30s. On every 16–30s reply the visitor sees "Something went wrong" while the backend succeeds, bills the AI call, and stores an unseen assistant message. **Verified** (both constants read directly). Category: Reliability. Confidence: High.
- **C2 — Signup rollback gap orphans the tenant and permanently locks the email.** `backend/routers/auth.py:172` inserts the tenant; `:221` logs "rolling back" but never deletes it, so a mid-signup `widget_configs`/FAQ failure bricks that email (500 on the attempt, 409 on every retry). Category: Reliability. Confidence: High.
- **C3 — Manual lead endpoint returns HTTP 200 with `lead_id:null` on a silent insert failure.** `backend/routers/widget_lead.py:138-175` — a lead the form reports as captured was never stored, with no log line and no owner alert. Category: Reliability. Confidence: High.
- **C4 — Conversations page load + reply fail silently.** `frontend/src/pages/ConversationsPage.jsx:225-229` (list) and `:408-410` (reply) — on an API outage the owner sees "no leads," and a failed reply to a real customer shows false success. Category: Reliability. Confidence: High.
- **C5 — Google Calendar outage presented as "fully free" → external double-booking.** `backend/services/google_calendar.py::get_busy_times` returns `[]` on any error; `booking.py:190-198` then offers already-booked slots. The DB `EXCLUDE` constraint guards only our table, not the tenant's real calendar. Category: Reliability. Confidence: High.

## Customer-PII exposure (Security)

- **SEC-H1 — Public widget key grants bulk customer-PII export via the iCal feed.** `backend/routers/appointments.py:595-695` gates the feed on `widget_configs.api_key` — the public embed credential visible in every tenant's page source — yet returns name/email/phone/notes for ~500 appointments over a 120-day window. Anyone who reads a tenant's HTML can download their full customer contact list. **Verified** (code path fully traced). Category: Security / Broken Access Control. Confidence: Confirmed.

## Widget unusable for keyboard / screen-reader visitors (Accessibility)

These affect **every tenant's end customers**, not just internal users — the widget is embedded across the entire customer base.

- **A11Y-W1 — Widget launcher is an unfocusable, unlabeled `<div>`.** `widget/agentnexlify-widget.js:921` — no `tabindex`/`role`/`aria-label`/key handler. Keyboard-only and screen-reader users cannot open the widget at all. **Verified.** WCAG 2.1.1 (A), 4.1.2 (A). Category: Accessibility. Confidence: High.
- **A11Y-W2 — Chat message stream is not a live region.** `widget/agentnexlify-widget.js:944` — `#anx-messages` has no `role="log"`/`aria-live`, so a screen-reader user never hears the AI's reply. **Verified.** Category: Accessibility. Confidence: High.
- **A11Y (2 further widget/dashboard blockers)** — see `audit-accessibility-launch-2026-07-09.md` BLOCKER section (4 total). The remaining two complete the "widget core flow is not operable by AT" set.

---

# HIGH (fix in the first patch train, not necessarily pre-launch)

Grouped by category. Full detail in the per-dimension files.

**Reliability (11):** lead-capture `lead_captured:true` derived from a regex, not the DB write (H1); no request idempotency on `/chat` → retries duplicate messages/leads/billing (H2); widget Claude call `max_retries=0` (H3); platform metrics silently truncate at 50k rows (H4); bid-request and restaurant-order chat captures lost on a single failed insert with the customer already told "done" (H5, H6); `send_sms()` failure return value ignored by every business-critical caller (H7); `appointment_booker` accepts free-text as an appointment id (H8, latent/unwired); frontend null-deref + dropped-rejection patterns that blank whole pages (H9–H11, capped to page scope by error boundaries).

**Accessibility (8):** form inputs without programmatic labels, focus not trapped/managed in the widget window, color-only status indicators, missing landmark/heading structure, non-descriptive link text — see the report's HIGH section.

**UI consistency (3):** plan display-name drift "Chatbot/Agent OS" (Billing + FreeWidget) vs "AI Front Desk/AI Workforce" (marketing/signup/wizard) on the two highest-trust surfaces — checkout and billing (H2); Admin Analytics plan map omits the two plans actually sold, mislabeling most paying tenants (H3); admin dashboards render on an off-brand indigo/coral palette instead of brand tokens (H1). H2 and H3 are 2-line, near-zero-regression fixes.

**Concurrency (1):** duplicate-lead creation via check-then-insert TOCTOU with **no** DB unique constraint on `leads(client_id, email/phone)` — confirmed against migrations; lead capture fans out on every chat message, so two quick messages create two lead rows and double-fire every downstream automation (owner alerts, sequences, scoring, webhook).

**Security (1, counted above as blocker-adjacent):** SEC-H1 iCal PII feed.

---

# Prioritized remediation plan

**P0 — before any launch (the blocker set, ~1–2 days):**
1. SEC-H1: strip `customer_email`/`phone`/`notes` from the iCal feed today (interim), then move to a dedicated revocable feed token distinct from the public embed key.
2. C1: set widget `FETCH_TIMEOUT_MS` above the server ceiling (e.g. 35s) — one constant, remember the byte-identical widget copy.
3. C3: raise 500 instead of returning `lead_id:null` 200 in `submit_lead`.
4. C2: delete the tenant row on the signup failure branch so retry works.
5. A11Y-W1/W2 (+ the other 2 blockers): make the launcher a real `<button>` with `aria-label`/`aria-expanded`; give `#anx-messages` `role="log"`/`aria-live`. Widget-only, self-contained.
6. C4: add an error state (distinct from empty) to the Conversations list + reply, mirroring the existing `setSmsError` pattern in the same file.
7. C5: distinguish "verified empty" from "could not verify" in calendar busy-times; suppress or flag slots when Google sync fails.

**P1 — first patch train (days, post-launch acceptable):**
- Concurrency H1: add `UNIQUE INDEX ... ON leads (client_id, lower(email)) WHERE email IS NOT NULL` (+ phone) via a numbered migration, switch insert to upsert with `on_conflict`.
- Reliability H3 (`max_retries=1-2`), H9–H11 + M10–M12 null-guards, H11 fetch timeout in `_client.js` (fixes infinite spinners app-wide).
- UI H2/H3 (plan-name centralization + admin plan map).
- Security M1 (billing admin secret fail-closed in prod) before enabling production refunds.
- Accessibility HIGH set (labels, focus management, color-only status).

**P2 — scheduled, deliberate:**
- Reliability architectural items (idempotent/durable lead+order+bid pipeline; transactional signup; SQL-side platform metrics; delivery-status contract for SMS/email/calendar).
- UI architectural items (kill the duplicate vertical-page system; de-inline admin dashboards onto shared token'd CSS; one themed admin-auth gate).
- Security architectural items (calendar/PII feed-token type; AI-usage-guard circuit breaker; one shared fail-closed admin dependency).

---

# Quick wins (safe, low regression risk)

Each is a small, local, obviously-correct change:
1. **C1** — bump widget `FETCH_TIMEOUT_MS` above 30s (one constant × 2 byte-identical copies).
2. **C3** — `submit_lead`: 500 instead of `lead_id:null` 200.
3. **C2** — delete tenant on signup failure branch.
4. **H3** — pass `max_retries=2` to the widget chat Claude call.
5. **H11** — add `AbortSignal.timeout` to `_client.js request()` (kills infinite spinners across pages).
6. **Null-guards** (Reliability H9, M10–M12, L4) — `?.`/`|| []` at ~10 cited lines.
7. **UI H2** — centralize plan display names; fix Billing + FreeWidget labels.
8. **UI H3** — add `chatbot`/`agent_os` to `AdminAnalyticsPage` `PLAN_LABELS`/`PLAN_COLORS` (2 lines).
9. **UI H1 / L2 / L3** — swap admin hardcoded hex for brand token vars; `#fff` → `--accent-contrast`; button radius → `--radius-sm`.
10. **SEC-L2/L3** — Twilio forwarded-header URL reconstruction; default absent `role` to least-privilege.
11. **SEC-H1 interim** — drop PII columns from the iCal feed (the token rework is the durable fix).
12. **Process (Reliability M1)** — fix the CLAUDE.md claim that pre-commit "blocks bare-except" (it only warns, and the regex misses the multi-line form) OR promote the check to a block.

# Requires architectural change / deeper investigation

- **Idempotency + durable delivery** on the lead/booking/order/bid pipeline (Reliability H1, H2, H5, H6): client message id on `/chat`; move background writes to a durable queue with retry + dead-letter; stop deriving `lead_captured` from regex.
- **Signup as one transactional unit** (C2 durable fix): single Supabase RPC or compensating deletes on every branch.
- **Platform metrics in SQL** (Reliability H4, M2): replace 50k fetch-and-dedup scans with `COUNT(DISTINCT)`/`GROUP BY` RPCs; cache; offload sync DB calls off the event loop.
- **Delivery-status contract** for SMS/email/calendar (Reliability C5, H7, M3, M4; Security "verified-vs-unverified"): explicit success/failed/degraded, checked and surfaced, not fire-and-forget.
- **Calendar/PII feed-token type** + audit of every `widget_configs.api_key`-gated endpoint (Security H1 root cause).
- **Duplicate vertical-page system** removal + de-inlined admin dashboards on shared token'd CSS (UI M1, H1, M4).
- **Duplicate-lead DB constraint + upsert** (Concurrency H1) — small migration but touches the hot capture path; land deliberately with the upsert change in the same PR.

---

# Release recommendation

## DO NOT SHIP in the current state — then ship with known risks once the P0 blocker set lands.

**Justification.** The core product promise is "never miss a lead, book appointments, embed anywhere." Three of the five dimensions each surface a launch blocker that breaks exactly that promise or leaks customer data:

- **Silent data loss on the revenue path** — the manual-lead endpoint reports success while dropping the lead (C3), the widget shows visitors an error while the backend quietly succeeds and bills (C1), and a signup hiccup permanently bricks a customer's email (C2). These are not edge cases; they sit on the primary money path.
- **A mass customer-PII exposure** — the public embed key, printed in every tenant's page source, downloads every customer's name/email/phone (SEC-H1). That is a GDPR-grade breach vector affecting every customer of every tenant.
- **The widget is unusable for keyboard and screen-reader visitors** — they cannot open it or hear a reply (A11Y-W1/W2), and this ships to every tenant's site, so the accessibility failure is replicated across the entire customer base.

What makes this a "do not ship *yet*" rather than a "do not ship, come back in a month": the blocker set is small (nine findings) and **most are quick, low-regression fixes** — a timeout constant, an error-status swap, a compensating delete, a `<div>`→`<button>`, and stripping PII columns from one endpoint. The deeper layers the audit exercised — JWT/webhook signature verification, Stripe idempotency, the tenant-scope helpers, the appointment double-booking `EXCLUDE` constraint, React error boundaries — are launch-grade and should not be touched.

**Path to green:** fix the P0 list (est. 1–2 focused days), re-verify each with the reproduction steps in the dimension reports, then launch with the P1/P2 items tracked as known, documented risks. After P0, the honest posture is **Ship with known risks** — the remaining High/Medium items degrade gracefully (page-scoped error boundaries, fail-closed auth, monitorable cost caps) and are safe to burn down in the first patch trains.

---
_Read-only audit — no application code modified. Verified: iCal PII feed path (`appointments.py:595-695`), widget↔server timeout mismatch (`agentnexlify-widget.js:1057` vs `widget_chat.py:1029`), `get_lead_score` unscoped `lead_id` (`leads.py:144-155`), duplicate-lead missing constraint (migrations 001/039/069), widget launcher `<div>` (`agentnexlify-widget.js:921`), plan-name drift (`BillingPage.jsx:14,21` vs `SignupPage.jsx:14,20`) — all confirmed by direct file read. Per-dimension reports carry the full evidence. — PASS_
