# Reliability & Failure-Handling Audit — Launch Readiness

**Date:** 2026-07-09
**Scope:** Read-only. Widget chat → lead capture → booking flow; signup → checkout flow; frontend failure states; swallowed errors; nullability; rollback gaps; retry/timeout; performance in hot paths.
**Method:** End-to-end trace via Read/Grep/Glob of the live source (`backend/routers/`, `backend/services/`, `frontend/src/`, `widget/`) plus two parallel sweeps (backend silent-failure, frontend missing-state). No files modified.

## Severity counts
- CRITICAL: 5
- HIGH: 11
- MEDIUM: 12
- LOW: 6

## One-line ship recommendation
**Do not ship to paying tenants until C1–C5 are fixed** — the revenue path (lead capture + booking + signup) has several places that report success while silently losing the lead/booking or stranding the user; the widget chat timeout mismatch alone strands users on every slow reply. Everything else can follow fast in the first patch train.

---

## Cross-cutting context (mitigations already in place)
- **React error boundaries exist** — top-level `frontend/src/main.jsx:113` + per-page `PageErrorBoundary` keyed on `currentPage` (`frontend/src/components/App.jsx:389`). A render crash in one page shows that page's error screen, not a full-app white-screen. This caps the blast radius of the frontend nullability crashes below (they degrade to a page-level "something went wrong", not a dead app).
- **Widget booking submit is well-built** — `widget/agentnexlify-widget.js:1742` handles 409 (slot taken), timeout via `AbortController`, error text, button re-enable.
- **Appointment DB write is well-guarded** — `backend/services/booking.py:215` `create_appointment` does a pre-insert overlap check + relies on the DB `EXCLUDE` constraint, maps conflicts to 409.
- **Stripe webhook is solid** — `backend/routers/stripe_webhooks.py` verifies signature, is idempotent (`check_and_record`), and releases the idempotency row on handler failure so Stripe retries (GH #308 fix at line 118).

---

# CRITICAL

## C1 — Widget chat client timeout (15s) is shorter than server timeout (30s): user sees an error while the backend succeeds
- **Category:** Reliability
- **Location:** `widget/agentnexlify-widget.js:1057` (`FETCH_TIMEOUT_MS = 15000`) + `:1064` (AbortController) vs `backend/routers/widget_chat.py:1029` (`timeout=30.0` on the Claude call)
- **Issue:** The widget aborts the `/api/v1/widget/chat` fetch at 15s. The backend's Anthropic call can legitimately run up to 30s (long context, rate-limit backoff, model latency). When Claude takes 16–30s, the browser aborts → user sees the `connectError` message (`widget/agentnexlify-widget.js:1475-1477`), but the backend keeps running, gets the reply, and **saves the assistant message to `chat_messages`** (`widget_chat.py:1198`) and fires lead capture.
- **Impact:** On every slow reply the visitor is told the chat failed and likely abandons — while the business is billed for the AI call and the conversation now contains an assistant message the user never saw. Next message ships that unseen turn back as history → desynced thread. Lead-capture may have already fired, so the "failure" the user saw actually processed.
- **Evidence:** client abort at 15s (`:1065`), server Claude timeout 30s (`widget_chat.py:1029`), unconditional save at `widget_chat.py:1198`.
- **Reproduction:** Embed widget; induce a 16–29s backend reply (large tenant KB / Anthropic 429 backoff). Widget shows "Something went wrong"; check `chat_messages` — the assistant reply is stored.
- **Recommended fix:** Set client `FETCH_TIMEOUT_MS` strictly greater than the server ceiling (e.g. 35s), or lower the server Claude `timeout` below the client's and return a graceful in-band "still thinking / try again" payload. Client timeout must always exceed server timeout.
- **Confidence:** High

## C2 — Signup rollback gap: tenant row created but widget_configs failure orphans it and permanently locks the email
- **Category:** Reliability
- **Location:** `backend/routers/auth.py:172` (tenant insert) → `:196-227` (widget_configs insert); dedup guard `:152-160`
- **Issue:** `_provision_tenant_account` inserts the `tenants` row first (`:172`). If the `widget_configs` insert then fails (`:197-216`), the code logs `"... - rolling back"` (`:221`) and raises HTTP 500 — **but nothing is rolled back**. The tenant row stays. On retry, the dedup check at `:152-160` finds the orphan and returns 409 "Email already registered".
- **Impact:** A transient DB blip mid-signup permanently bricks that email: the user can neither finish signup (500) nor retry (409), and has a tenant with no `api_key`/widget and no way in. The log message actively lies ("rolling back"). Same shape if `_seed_industry_faqs` (`:229`) raises.
- **Evidence:** insert at `:172`, no `db.table("tenants").delete()` anywhere in the failure branch, misleading log at `:220-224`, dedup 409 at `:159-160`.
- **Reproduction:** Force `widget_configs.insert` to raise (e.g. unique/constraint error) after the tenant insert; observe orphan tenant + 409 on retry with the same email.
- **Recommended fix:** Wrap provisioning so a widget_configs/faq failure deletes the just-created tenant row before raising, or make the whole thing a single transactional RPC. At minimum, delete the tenant on the failure path so retry works.
- **Confidence:** High

## C3 — Manual lead endpoint returns HTTP 200 "success" with `lead_id: null` when the insert silently returns no rows
- **Category:** Reliability
- **Location:** `backend/routers/widget_lead.py:138-175` (`submit_lead`)
- **Issue:** After the insert (`:150 result = db.table("leads").insert(...).execute()`), the code only sets `lead_id` when `result.data` is truthy (`:151-153`). If the insert returns no data (RLS block, silent write failure) without raising, `lead_id` stays `None`, no branch logs it, and the endpoint returns `WidgetLeadResponse(lead_id=None, updated_fields=[...])` with HTTP 200.
- **Impact:** The widget/embed form gets a 200 and reports the lead captured; the lead was never stored and no owner alert / scoring / qualification fires (all gated on `if lead_id`). A silently lost lead on the primary money path, with no log line to even detect it. (The sibling `submit_offline_contact` at least logs `"INSERT returned no data"` at `:243`; this path does not.)
- **Evidence:** `:150-153` conditional assignment, `:172-175` unconditional 200 return, no `else`/log on empty `result.data`.
- **Reproduction:** Make the leads insert return empty data (RLS/policy). POST `/api/v1/widget/lead` → 200 with `lead_id: null`, no lead row, no owner alert.
- **Recommended fix:** If `not result.data` after insert, log an error and raise 500 (or a typed "lead not saved" response) so the caller can retry. Never return 200 with a null id on the lead path.
- **Confidence:** High

## C4 — Conversations page: the lead list and outbound replies fail silently and look like "no leads yet"
- **Category:** Reliability
- **Location:** `frontend/src/pages/ConversationsPage.jsx:225-229` (list load) and `:408-410` (`replyToConversation`)
- **Issue:** The conversation-list load catch only `console.error`s and leaves `conversations` empty (`:225-229`); the empty-state UI at `:774` ("Conversations from your chat widget will appear here") renders identically to a real API failure. Separately, `replyToConversation` swallows a send failure (`:408-410`) and returns the button to "Send" with no error — the agent believes the reply to the lead went out.
- **Impact:** This is the tenant's primary lead-handling surface. On an API outage the owner sees "no conversations" and assumes no leads; a failed reply to a real customer vanishes with a false success. (Contrast `handleSendSms` at `:415-438`, which correctly surfaces `setSmsError`.)
- **Evidence:** list catch `:225-229`, reply catch `:408-410`, indistinguishable empty state `:774`.
- **Reproduction:** Return 500 from the conversations endpoint → page shows empty state. Fail the reply POST → button resets, no error, no message sent.
- **Recommended fix:** Add an error state distinct from empty for the list; surface reply failures (mirror the SMS handler's `setSmsError` pattern) and keep the draft.
- **Confidence:** High

## C5 — Google Calendar outage is presented as "calendar fully free" → the widget offers already-booked slots (external double-booking)
- **Category:** Reliability
- **Location:** `backend/services/google_calendar.py` `get_busy_times` (`except Exception: ... return []`) consumed by `backend/services/booking.py:190-198` `generate_available_slots`
- **Issue:** When the tenant has a Google Calendar integration, available slots subtract Google busy times. Any Google API failure — expired OAuth token, rate limit, transient 5xx — is caught and returns `[]`, indistinguishable from "no events." The slot generator then treats the day as wide open.
- **Impact:** The widget confidently offers a slot the owner already has booked in Google. The DB `EXCLUDE` constraint only guards against conflicts in *our* `appointments` table, not the tenant's real calendar, so the booking succeeds and looks like success to everyone. Double-booked owners is a direct trust/churn hit on the product's core promise.
- **Evidence:** `google_calendar.py get_busy_times` empty-list-on-exception; `booking.py:190-198` best-effort merge with `except Exception: logger.warning(...)` then continues.
- **Reproduction:** Revoke/expire the tenant's Google token; request slots — days with real Google events are offered as free.
- **Recommended fix:** Distinguish "no busy times" from "could not verify." On failure, either suppress that day's slots, or flag the resulting appointment for manual confirmation and raise a tenant-visible "calendar sync degraded" warning.
- **Confidence:** High (identified by backend sweep; mechanism verified against `booking.py` best-effort merge)

---

# HIGH

## H1 — `lead_captured: true` is returned from a regex match, not from the actual DB write (which is a best-effort background task)
- **Category:** Reliability
- **Location:** `backend/routers/widget_chat.py:1244-1249` + `:1328`; real write in `backend/routers/widget_lead_helpers.py:342` `_capture_leads_from_session`, outer swallow at `:642-643`
- **Issue:** The chat response sets `lead_captured=_has_contact`, where `_has_contact` is purely a regex hit on the message (`:1244`). The real insert happens later in a FastAPI `BackgroundTask` whose outermost handler swallows every exception with a single log line (`widget_lead_helpers.py:642-643`), and the new-lead insert failure path just logs and returns (`:556-561`, `:639-640`).
- **Impact:** The widget (and any consumer gating on `lead_captured`) is told the lead is captured while the row may never have been written — no owner alert, no automation. Background tasks also die entirely if the worker restarts between response and execution.
- **Evidence:** `widget_chat.py:1244,1328`; `widget_lead_helpers.py:554-561,639-643`.
- **Reproduction:** Force the leads insert in `_capture_leads_from_session` to fail; response still returns `lead_captured:true`; no lead row, no alert.
- **Recommended fix:** Either stop advertising `lead_captured` as a guarantee, or make the capture write synchronous far enough to know it succeeded; add a durable retry/dead-letter for the background insert.
- **Confidence:** High

## H2 — Widget `/chat` has no request idempotency → user retries (or the C1 false-timeout) duplicate messages, lead capture, and AI billing
- **Category:** Reliability
- **Location:** `backend/routers/widget_chat.py` (endpoint) — no idempotency key; `_save_chat_messages` (`widget_chat_helpers.py:461`) inserts unconditionally
- **Issue:** There is no client-supplied idempotency token on the chat request. After the C1 false 15s timeout (or any user retry), the same message is reprocessed: a second Claude call (billed), duplicate user+assistant rows, and a second `_capture_leads_from_session` run.
- **Impact:** Duplicate billing and duplicate/again-processed leads on exactly the failure the user is most likely to retry.
- **Evidence:** no idempotency check in the endpoint; unconditional insert `widget_chat_helpers.py:493`.
- **Reproduction:** Send a message, let it time out client-side, retry the same text → two Claude calls + duplicate messages.
- **Recommended fix:** Accept a client message id; short-circuit on replay (mirror the Stripe `check_and_record` pattern already in the codebase).
- **Confidence:** High

## H3 — Widget chat Claude call runs with `max_retries=0`: a single transient Anthropic 429/overload gives the user an error
- **Category:** Reliability
- **Location:** `backend/routers/widget_chat.py:1021-1035` (call) → `backend/services/llm_runtime.py:263,348` (`max_retries` defaults to `0`, not passed by widget chat)
- **Issue:** `call_claude_messages` supports retry with backoff (`llm_runtime.py:283-319`) but defaults `max_retries=0`, and the widget chat call does not override it. Any `RateLimitError`/overloaded/timeout results in the generic "I'm having trouble right now" fallback (`widget_chat.py:1067-1091`) on the first transient error.
- **Impact:** Under Anthropic rate limiting or brief overload, real visitors get a dead-end apology instead of a one-retry recovery — on the revenue path.
- **Evidence:** default `max_retries: int = 0` (`llm_runtime.py:263`); widget chat call omits the arg (`widget_chat.py:1022-1035`); retry logic exists but is gated on `attempts <= max_retries` (`:305`).
- **Reproduction:** Return a 429 from Anthropic once; observe immediate fallback with no retry.
- **Recommended fix:** Pass `max_retries=1-2` with the existing backoff for the widget chat call (retries run in the executor thread, so the loop isn't blocked).
- **Confidence:** High

## H4 — Platform funnel + tenant-health metrics silently truncate at 50k rows with no `errors` flag → wrong counts and churn misclassification
- **Category:** Performance / Reliability
- **Location:** `backend/services/funnel_metrics.py:139-209` and `backend/services/tenant_health.py:139-203` (each `.limit(50000)` full-table fetch)
- **Issue:** `activated`, `with_leads`, `new_leads_week`, `new_appointments_week` (funnel) and all per-tenant activity (health) are computed by pulling entire tables into memory capped at 50k rows and deduping in Python. Once `chat_messages`/`leads` exceed 50k, rows are silently dropped. Unlike a DB error, the cap adds nothing to the `errors` list — the number just reads low.
- **Impact:** Funnel metrics under-report activation/leads as the platform grows (undetectable). In `tenant_health`, truncation drops recent activity for some tenants → they're misclassified `dormant` and fed into the wrong convert/retain motion. Also: every admin dashboard load pulls up to 3×50k rows synchronously into a process with no caching.
- **Evidence:** `funnel_metrics.py:143,162,181,197`; `tenant_health.py:143,166,189`; cap comment admits "counts will be approximate" (`tenant_health.py:23-27`).
- **Reproduction:** Seed >50k `chat_messages`; compare `activated` to a `SELECT COUNT(DISTINCT tenant_id)`.
- **Recommended fix:** Move the aggregation to SQL (`GROUP BY`/`COUNT(DISTINCT)` via RPC) instead of fetch-and-dedup; if a cap is retained, flag truncation in the response. Cache the admin computation.
- **Confidence:** High

## H5 — Contractor bid requests captured in chat have no owner-alert fallback: a single failed insert loses the whole request
- **Category:** Reliability
- **Location:** `backend/routers/widget_booking.py:398-461` (`_process_bid_request_from_chat`)
- **Issue:** A validated bid request (scope, budget, timeline, customer contact) is written to `action_items` and nothing else. If that insert fails (`:444-459`), it logs and returns. Unlike the order flow, there is no SMS/email to the owner, no webhook, no retry.
- **Impact:** A high-intent contractor lead the visitor just typed into chat is gone with one log line.
- **Evidence:** `:444-459` single insert + `except: logger.exception`; no notification code follows.
- **Recommended fix:** Mirror the order-notification path (owner SMS/email) and/or add durable retry for failed `action_items` inserts.
- **Confidence:** High

## H6 — Restaurant order insert failure: customer was already told "order placed," owner never notified
- **Category:** Reliability
- **Location:** `backend/routers/widget_booking.py:184-193` (`_process_order_from_chat`); AI is instructed to confirm placement in `backend/routers/widget_chat_helpers.py:695-696`
- **Issue:** The AI tells the customer the order is placed, then the background task inserts the `orders` row. If the insert fails or returns no data (`:186-192`), the function returns before any SMS/email — the owner gets nothing.
- **Impact:** Customer believes they ordered; no order exists; owner never finds out. Lost revenue + bad customer experience.
- **Evidence:** `:185-193` return-on-failure before the notification block (`:221+`).
- **Recommended fix:** On insert failure still send the owner a degraded "order details, please confirm manually" alert; don't return silently.
- **Confidence:** High

## H7 — `send_sms()` returns `False` on failure but every business-critical caller ignores the return value
- **Category:** Reliability
- **Location:** `backend/services/twilio_service.py:26-78` (returns `bool`); callers `backend/services/lead_alerts.py:153-170`, `backend/routers/widget_booking.py:230-235` & `:301-304`, `backend/services/booking.py:374-385`, `backend/routers/widget_chat.py:1157-1168`
- **Issue:** `send_sms` never raises past its own internal `try/except` (it returns `False`). Callers wrap it in `try/except Exception`, which can't catch a `False`. So when Twilio is unconfigured or a send fails after retries, the caller's "SMS FAILED" log never fires — the only trace is one generic line in `twilio_service.py` with no lead/tenant/order context.
- **Impact:** The "never miss a lead" promise rides on SMS delivery, yet delivery failures are invisible and un-attributable across the fleet.
- **Evidence:** return-`False` contract (`twilio_service.py`); `await send_sms(...)` inside try/except with no boolean check at every listed caller.
- **Recommended fix:** Check the boolean (or return `(ok, sid)`) and log failure with the lead/order/tenant context the caller already holds.
- **Confidence:** High

## H8 — appointment_booker accepts a managed-agent's free-text reply as the appointment id and reports `status="booked"` (latent landmine)
- **Category:** Reliability
- **Location:** `backend/services/appointment_booker.py:276-304`
- **Issue:** `appointment_id = reply_stripped.splitlines()[0].strip()` — the first line of the agent's reply is taken as the booking reference with no UUID validation and no check that an `appointments` row exists, then returned as `status="booked"` with a customer-facing "Appointment confirmed. Reference: …".
- **Impact:** Any hallucinated/garbled non-`NEEDS_HUMAN` reply reports a fake confirmed booking. **Currently latent** — the runner is defined in `managed_agents_registry.py:246` but not called from any router — so no live path hits it today. It will silently mis-book the moment someone wires it up.
- **Evidence:** `:276-304`; caller search shows only `managed_agents_registry.py` references, no router.
- **Recommended fix:** Validate `appointment_id` is a UUID and confirm the row exists before returning `booked`; otherwise return `needs_human`/`error`. Fix before wiring it into any flow.
- **Confidence:** High

## H9 — Analytics page: a null 200 body crashes the whole page; 6 of 7 parallel fetch failures are dropped
- **Category:** Reliability
- **Location:** `frontend/src/pages/AnalyticsPage.jsx:371-414` (dropped rejections), `:372,376,380,391` (unguarded `.value.data` on possibly-null body)
- **Issue:** `_client.js` legitimately returns `null` on a 204/empty-200; `Promise.allSettled` marks that "fulfilled", so `conv.value.data` throws `TypeError` (`:372`), caught at `:415` → the whole page drops into the error branch, discarding every already-loaded section. Separately, each `if (x.status === "fulfilled")` has no `else`, so rejected overview/leads/response/widget/sources calls vanish; empty charts look identical to an empty tenant.
- **Impact:** One empty endpoint blanks the entire analytics page (contained to the page by `PageErrorBoundary`); partial outages silently show wrong/empty data.
- **Evidence:** `:371-414`, null-deref at `:372,376,380,391`.
- **Recommended fix:** `conv.value?.data || []` guards; add `else` branches that set per-section error flags.
- **Confidence:** High

## H10 — Calendar page shows an empty calendar on load failure (bookings look like they vanished)
- **Category:** Reliability
- **Location:** `frontend/src/pages/Calendar.jsx:76-77`
- **Issue:** `catch { setAppointments([]); }` with no `setError`. A network/500 makes existing bookings disappear with no indication of failure. (Create-appointment at `:170-171` is correctly handled.)
- **Impact:** Owner believes appointments were lost; may double-book or panic.
- **Recommended fix:** Set a distinct error state and keep prior data on refresh failure.
- **Confidence:** High

## H11 — No fetch timeout anywhere in the frontend API client → any backend stall = permanent spinner
- **Category:** Reliability
- **Location:** `frontend/src/utils/api/_client.js:62-78` (`request()` calls `fetch()` with no `AbortController`/`AbortSignal.timeout`)
- **Issue:** A backend that accepts the connection then stalls never settles the promise, so pages that clear their spinner in `finally` never reach `finally`. Network *rejection* is handled well (`ApiError(0,...)`); the gap is stalls/timeouts.
- **Impact:** Infinite spinners across Conversations, Analytics, Admin, Calendar on a hung backend. Fixing this one function covers most pages.
- **Recommended fix:** Add `AbortSignal.timeout(n)` (or manual AbortController) to `request()`.
- **Confidence:** High

---

# MEDIUM

## M1 — Pre-commit "bans bare-except" is only a WARNING and its regex misses the common multi-line form
- **Category:** Reliability (process)
- **Location:** `scripts/hooks/pre-commit` CHECK 3 (`WARNINGS=$((WARNINGS + 1))`, not `ERRORS`); exit logic "`$WARNINGS warning(s) found. Committing anyway.`"
- **Issue:** CLAUDE.md §Automation states the pre-commit hook "blocks … bare-except blocks." It does not block — it warns and commits anyway. The detection regex is `except.*:.*pass\|except:$`, which only matches same-line `except: pass`; the far more common `except Exception:` / `except:` followed by `pass` on the next line is not caught at all.
- **Impact:** The guardrail the team believes protects the "best-effort/never-raises" codebase from swallowing errors is effectively off. Every silent-failure finding in this report passed the hook.
- **Evidence:** CHECK 3 warning-only; multi-line miss in the regex; CLAUDE.md claim vs behavior.
- **Recommended fix:** Either promote to `ERRORS` (block) or fix the wording in CLAUDE.md; broaden the regex to multi-line `except…:\n\s*pass`.
- **Confidence:** High

## M2 — Synchronous Supabase client calls run inside async request handlers → event-loop blocking on hot paths
- **Category:** Performance
- **Location:** e.g. `backend/routers/auth.py:335` `register` (async) calls sync `_provision_tenant_account` (multiple blocking DB calls `:152-229`); `funnel_metrics.py`/`tenant_health.py` sync full-table fetches invoked from async admin routes
- **Issue:** The Supabase Python client is synchronous; these calls are not offloaded to a thread, so they block the Uvicorn event loop for the duration of each DB round-trip. Signup does 3–4 serial blocking writes.
- **Impact:** Under concurrency, one slow query stalls all requests on that worker (4 workers in prod per `python-fastapi.md`). The widget chat Claude call is correctly offloaded (`llm_runtime.call_claude_messages` uses `run_in_executor`), but DB calls generally are not.
- **Recommended fix:** Offload blocking DB work via `run_in_executor`/`asyncio.to_thread` on hot paths (signup, admin aggregates), or batch signup writes into one RPC.
- **Confidence:** Medium

## M3 — `send_email()` structured failure result is discarded in lead alerts
- **Category:** Reliability
- **Location:** `backend/services/lead_alerts.py:133-150` consuming `backend/services/email_sender.py:225-231`
- **Issue:** `send_email` returns `{"success": False, "detail": "resend_api_key not configured" | "daily_limit_reached"}` instead of raising. `_send_email_alert` never checks `result["success"]`, so a misconfigured Resend key or a hit daily cap silently no-ops the new-lead email with no lead/tenant-framed log.
- **Recommended fix:** `if not result.get("success"): logger.error("lead_alert email FAILED tenant=%s lead=%s reason=%s", ...)`.
- **Confidence:** High

## M4 — Billing reconciliation reports "0 used" on a DB read error → masks an over-cap tenant
- **Category:** Reliability
- **Location:** `backend/services/billing_reconciliation.py:220-268`
- **Issue:** On a read failure of `os_tenant_usage` / `tenant_ai_usage_monthly`, the code sets usage to `0` and continues. Since `0` feeds `any_over_cap`, a transient DB error reads as "fine" — the exact drift the reconciler exists to catch is hidden by its own error handling.
- **Recommended fix:** Add a `data_incomplete` flag; exclude incomplete rows from any automated "all clear."
- **Confidence:** Medium

## M5 — ConversationsPage: switching conversations shows the previous thread under the new header
- **Category:** Reliability
- **Location:** `frontend/src/pages/ConversationsPage.jsx:236-256`
- **Issue:** `selected` updates immediately but `messages` isn't cleared before the fetch nor reset on failure (`:249-251`). The agent can read the prior conversation's messages under a different lead's name.
- **Recommended fix:** `setMessages([])` before fetch; reset on error.
- **Confidence:** High

## M6 — ConversationsPage: a transient snippet error poisons the cache for the whole session
- **Category:** Reliability
- **Location:** `frontend/src/pages/ConversationsPage.jsx:336-339` (caches `[]` on error) + cache-hit guard `:330`
- **Issue:** On error the empty array is cached; the guard then blocks all retries → permanent false "No snippets" until reload.
- **Recommended fix:** Don't cache on failure; allow retry.
- **Confidence:** High

## M7 — Admin pages blank the entire body during any refresh
- **Category:** Reliability (UX)
- **Location:** `frontend/src/pages/AdminFunnelPage.jsx:415,468` + `AdminTenantHealthPage.jsx:542,603`
- **Issue:** Skeleton requires `!data`, content requires `!loading`; a refresh with existing data matches neither branch, so the body vanishes until the request resolves. Combined with H11 (no timeout), a hung refresh blanks the page indefinitely.
- **Recommended fix:** Keep prior data visible during refresh; show an inline spinner.
- **Confidence:** High

## M8 — AdminAnalyticsPage: all 7 fetches `.catch → null` with only `console.warn`; no error banner
- **Category:** Reliability
- **Location:** `frontend/src/pages/AdminAnalyticsPage.jsx:119-146`
- **Issue:** If the API is down, every section shows its "No data yet" empty state; the admin can't tell failure from empty.
- **Recommended fix:** Add a page-level error banner when fetches reject.
- **Confidence:** High

## M9 — TriggerLogsPage: empty catches swallow errors and show empty logs
- **Category:** Reliability
- **Location:** `frontend/src/pages/TriggerLogsPage.jsx:335-336` and `:347-348` (`catch { setLogs([]); } / setRules([]);`)
- **Issue:** A failed load is indistinguishable from "no automation activity."
- **Recommended fix:** Distinct error state.
- **Confidence:** High

## M10 — AnalyticsPage: Peak Hours renders a blank chart on empty array; visible "NaN min"
- **Category:** Reliability (UX)
- **Location:** `frontend/src/pages/AnalyticsPage.jsx:702` (`widgetData?.peak_hours ?` truthy instead of `.length > 0`), `:899` (`Math.round(avg_duration_seconds/60)` → "NaN min" when missing)
- **Recommended fix:** Gate on `.length > 0`; `?? 0` before `Math.round`.
- **Confidence:** High

## M11 — AnalyticsPage tick formatters crash the render tree on a null date
- **Category:** Reliability
- **Location:** `frontend/src/pages/AnalyticsPage.jsx:556,644,787` (`tickFormatter={d => d.slice(5)}`)
- **Issue:** Throws if any row `date` is null; contained to the page by `PageErrorBoundary` but shows a crash screen for all of Analytics.
- **Recommended fix:** Null-guard the formatter.
- **Confidence:** High

## M12 — AdminAnalyticsPage: unguarded `weeklyGrowth.daily_data.length` crashes the page
- **Category:** Reliability
- **Location:** `frontend/src/pages/AdminAnalyticsPage.jsx:484` (only `weeklyGrowth` guarded, at `:391`, not `daily_data`)
- **Issue:** If `/weekly-growth` omits `daily_data`, `.length` on undefined throws.
- **Recommended fix:** `weeklyGrowth?.daily_data?.length`.
- **Confidence:** High

---

# LOW

## L1 — `_save_chat_messages` swallows persistence failure with no escalation
- **Category:** Reliability
- **Location:** `backend/routers/widget_chat_helpers.py:461-510` (returns `[]` on exception)
- **Issue:** Chat persistence failure is logged once and returns `[]`. Since `_load_chat_history` drives lead capture, categorization, and action-item extraction, a sustained DB issue quietly degrades those with no alert. Low because the customer-visible reply still returns.
- **Recommended fix:** Add a failure counter/alert threshold.
- **Confidence:** Medium

## L2 — Lead-capture dedup failure fabricates an empty result → creates a duplicate lead
- **Category:** Reliability
- **Location:** `backend/routers/widget_lead_helpers.py:396-400` and `:481-486`
- **Issue:** On a transient error during the dedup `SELECT`, the code sets `existing = <empty>` and proceeds to create a *new* lead, even if one exists. Doesn't lose data, but silently duplicates lead rows on error paths, polluting counts.
- **Recommended fix:** On dedup error, abort/retry rather than fall through to insert.
- **Confidence:** High

## L3 — appointment_booker best-effort lead status update swallowed
- **Category:** Reliability
- **Location:** `backend/services/appointment_booker.py:280-293`
- **Issue:** Even on a genuine booking, the `leads.status="appointment_booked"` update failure is swallowed, so the dashboard can show a booked lead as still "new." (Latent with H8.)
- **Confidence:** Medium

## L4 — PipelinePage: unguarded stage-name access
- **Category:** Reliability
- **Location:** `frontend/src/pages/PipelinePage.jsx:461-462` (`s.name.toLowerCase()`)
- **Issue:** Throws if any stage lacks `name`. (Tags at `:363` are safely gated.)
- **Recommended fix:** `(s.name || "").toLowerCase()`.
- **Confidence:** High

## L5 — AdminFunnelPage: a present-but-wrong-shaped 200 renders nothing
- **Category:** Reliability
- **Location:** `frontend/src/pages/AdminFunnelPage.jsx:441,468`
- **Issue:** If `total_tenants` is absent, neither empty nor content state matches → blank with no error.
- **Confidence:** Medium

## L6 — AdminTenantHealthPage: raw browser error shown verbatim; empty catch hides corrupt timestamps
- **Category:** Reliability (UX)
- **Location:** `frontend/src/pages/AdminTenantHealthPage.jsx:433-434` (raw `err.message`), `:70-81` (`formatDate` returns `"-"` on parse error, no log)
- **Recommended fix:** Map errors to offline/auth/server categories; log parse failures.
- **Confidence:** High

---

# Quick wins (high value, low effort)
1. **Bump widget `FETCH_TIMEOUT_MS` above the server's 30s** (C1) — one constant in `agentnexlify-widget.js` (remember byte-identical copy in `frontend/public/widget/`).
2. **Add `AbortSignal.timeout` to `_client.js request()`** (H11) — one function, fixes infinite spinners app-wide.
3. **Raise 500 instead of returning `lead_id:null` 200** in `submit_lead` (C3).
4. **Delete the tenant row on the signup failure path** (C2) so retry works.
5. **Pass `max_retries=2` to the widget chat Claude call** (H3).
6. **Null-guard the frontend derefs** (H9, M10–M12, L4): `?.`/`|| []` at the ~10 cited lines.
7. **Add error states to Conversations list/reply and Calendar load** (C4, H10) — mirror existing `setSmsError`/`setAddError` patterns already in the same files.
8. **Fix CLAUDE.md's pre-commit claim or promote the bare-except check to a block** (M1).

# Architectural changes (larger, schedule deliberately)
1. **Idempotency + durable delivery on the lead/booking pipeline** (H1, H2, H5, H6): give `/chat` a client message id; move background lead/order/bid writes to a durable queue with retry + dead-letter, so a worker restart or single insert failure can't lose a lead/order/bid. Stop deriving `lead_captured` from regex.
2. **Signup as one transactional unit** (C2): a single Supabase RPC that creates tenant + widget_config + FAQ seeds atomically, or compensating deletes on every failure branch.
3. **Move platform metrics to SQL aggregation** (H4, M2): replace fetch-and-dedup 50k scans with `COUNT(DISTINCT)`/`GROUP BY` RPCs; cache admin computations; offload remaining sync DB calls off the event loop.
4. **A delivery-status contract for external side effects** (C5, H7, M3, M4): treat SMS/email/calendar as operations with an explicit success/failed/degraded status that is checked, surfaced to the tenant, and retried — not fire-and-forget best-effort. Distinguish "verified empty" from "could not verify" everywhere (calendar busy-times, usage reconciliation).

---
_Read-only audit. Verified: pre-commit exit logic (warnings don't block), widget↔server timeout mismatch (15s vs 30s), signup rollback gap (no tenant delete on failure), submit_lead null-return path, funnel/health 50k caps, appointment_booker unwired, ErrorBoundary scope — all confirmed by direct file reads. Frontend line-level findings cross-checked against `_client.js` and the cited pages. — PASS_
