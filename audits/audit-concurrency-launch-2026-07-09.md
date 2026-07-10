# Concurrency, Idempotency & State-Integrity Audit — Launch Readiness

**Date:** 2026-07-09
**Scope:** Race conditions, duplicate side effects, multi-worker state, frontend double-submit, React effect hygiene, stale/optimistic state, response ordering.
**Method:** Read-only trace of real flows (backend + widget + frontend) against migrations. No code modified.
**Environment fact:** Production runs 4 Uvicorn workers — in-memory state is per-process only.

---

## Severity counts

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 2 |
| LOW | 3 |
| Verified-safe (no action) | 6 |

**Single worst finding:** Duplicate lead creation via check-then-insert TOCTOU (H1). Lead capture fires as a background task on *every* chat message, dedups by SELECT-then-INSERT on `leads.email`/`phone`, and there is **no DB unique constraint** to catch the race — so two messages arriving close together in one session create two lead rows for the same visitor.

---

## HIGH

### H1 — Duplicate lead creation (check-then-insert TOCTOU, no DB backstop)
- **Category:** Race Condition
- **Location:** `backend/routers/widget_lead_helpers.py:342` (`_capture_leads_from_session`), dedup at `:390-395` (email) and `:470-480` (phone); insert at `:555`. Call site: `backend/routers/widget_chat.py:1251` (background task added on every chat message).
- **Issue:** Dedup is `SELECT leads WHERE email=? LIMIT 1` → if none, `INSERT`. The `leads` table has **no** `UNIQUE(client_id, email)` or `UNIQUE(client_id, phone)` constraint (confirmed: `migrations/001_initial_schema.sql` + `migrations/039_leads_index.sql` + `069` only add plain indexes; the only UNIQUE near leads is `tenants.owner_email`). Nothing serializes concurrent inserts.
- **Impact:**
  - Duplicate lead rows for the same visitor. Because each duplicate gets a distinct `lead_id`, every downstream per-lead action double-fires: owner SMS + email alert (M1 dedup keys on `lead_id`, so it does **not** catch these), `trigger_sequence("new_lead")`, `enroll_lead_in_sequences`, lead scoring, `lead.created` webhook. Duplicate customer-facing messages, skewed funnel metrics, duplicate automation enrollments.
- **Evidence:** `_capture_leads_from_session` is enqueued on every `POST` chat turn (`widget_chat.py:1251`). A visitor who supplies an email in message N and sends message N+1 quickly spawns two concurrent background tasks; both run the SELECT before either commits (`:390`, `:555`), both insert. No `on_conflict`/upsert, no advisory lock.
- **Reproduction:** Send two chat messages ~50ms apart in one session, both after the email is present in history. Observe two `leads` rows with identical `email` + `client_id`. (Two separate visitors sharing an email reproduce it too, but the single-session self-collision is the common path.)
- **Recommended fix:** Add `CREATE UNIQUE INDEX CONCURRENTLY ... ON leads (client_id, lower(email)) WHERE email IS NOT NULL;` (+ phone variant) via a numbered migration, then switch the insert to `upsert(..., on_conflict="client_id,email", ignore_duplicates=True)` and treat "no inserted row" as "existing lead → update path" (mirror the pattern already used in `services/idempotency.py:44`). This closes the race atomically at the DB and reuses a proven in-repo pattern.
- **Confidence:** High on the race and the missing constraint. Medium that duplicates are frequent in practice (depends on visitor typing cadence), but the per-message fan-out makes it materially likely at launch volume.

---

## MEDIUM

### M1 — New-lead owner alert dedup is per-worker in-memory
- **Category:** Reliability
- **Location:** `backend/services/lead_alerts.py:50` (`_alerted: set`), `:55` (`_already_alerted`), consumed by `send_new_lead_alert` at `:193`.
- **Issue:** Idempotency guard is a module-level `set()` keyed on `(tenant_id, lead_id)`. With 4 workers it dedups only within one process. The code comment acknowledges this as a deliberate soft cap.
- **Impact:** Same lead alerted from two workers → duplicate owner SMS (Twilio cost) + duplicate email. Worse in combination with H1: duplicate lead rows have different `lead_id`s, so this guard cannot dedup them at all — every H1 duplicate is also a duplicate alert.
- **Evidence:** `_alerted` is process-local; comment at `:43-49` states "at worst a second worker could send one duplicate." Both alert shims (`_send_new_lead_sms_notification`, `_send_new_lead_email_notification`) delegate to the same `send_new_lead_alert`, so within one worker/one task the second call is deduped — the gap is strictly cross-worker and cross-duplicate-row.
- **Reproduction:** Trigger the same lead's alert path on two workers (e.g. a ret/re-enqueued capture landing on a different worker), or rely on H1 producing two lead_ids. Owner receives two alerts.
- **Recommended fix:** Back the dedup with a DB claim — reuse `idempotency_keys` (`provider="lead_alert"`, `key=f"lead_alert:{tenant_id}:{lead_id}"`) via the existing atomic `check_and_record`. Fixing H1 first shrinks this to the rare true cross-worker case.
- **Confidence:** High (mechanism is explicit in code + comments).

### M2 — Dashboard live-data effect has no out-of-order / cancellation guard
- **Category:** Race Condition
- **Location:** `frontend/src/pages/ConversationsPage.jsx:198` (`load` useCallback) + `:232` (effect that calls `load()` on dep change). Deps: `channelFilter`, `serverSearch`.
- **Issue:** Rapid filter/search changes fire overlapping `load()` calls with no `ignore`/`AbortController` flag. Whichever response resolves last wins (`setConversations`), not whichever was requested last. A slow earlier request can clobber a fresh later one.
- **Impact:** Operator sees stale conversation list that doesn't match the active filter until the next manual change. Read-only display data — no data corruption, but confusing during live triage.
- **Evidence:** Effect body is just `load()` with `return` cleanup absent (`:232-234`); `load` awaits `Promise.all([...])` then unconditionally `setConversations`.
- **Reproduction:** Type a search, immediately change the channel filter; if the first request is slower, the list flips back to the first result set.
- **Recommended fix:** Standard `let ignore = false; ...; if (!ignore) setState; return () => { ignore = true; }` inside the effect, or an `AbortController` per request.
- **Confidence:** High.

---

## LOW

### L1 — Weekly funnel report dedup is per-worker in-memory
- **Category:** Reliability
- **Location:** `backend/services/weekly_funnel_report.py:28` (`_last_sent_date`), `:82`.
- **Issue:** Once-per-Monday guard is a module global. Not cross-worker on its own.
- **Impact:** Mostly mitigated: the send runs inside the automation tick, which holds the cross-worker DB lease (see S6), so only one worker executes it. Residual exposure is a worker restart mid-Monday resetting the global → at most one duplicate owner email. Acknowledged in the module docstring.
- **Recommended fix:** Optional — persist last-sent in a small table/row if even one duplicate is unacceptable. Otherwise accept as documented.
- **Confidence:** High.

### L2 — Signup submit has no re-entry guard (thin double-POST window)
- **Category:** Reliability
- **Location:** `frontend/src/pages/SignupPage.jsx:107` (`handleSubmit`); button `disabled={loading || googleLoading}` at `:477`.
- **Issue:** `handleSubmit` sets `loading` but has no `if (loading) return` at the top. React state is async, so a very fast double-click before the disabled re-render can invoke `/auth/register` twice.
- **Impact:** Low blast radius — the second register with the same email returns 4xx (duplicate), so no duplicate account and no duplicate charge (Stripe checkout is a later, separate redirect). Worst case is a confusing error toast.
- **Recommended fix:** Add `if (loading) return;` as the first line of `handleSubmit` (belt-and-suspenders alongside the disabled attribute).
- **Confidence:** High on the window; Low on impact.

### L3 — Dead dedup branch references a never-populated field
- **Category:** Reliability (correctness, not concurrency)
- **Location:** `backend/routers/widget_lead_helpers.py:413-417`.
- **Issue:** The existing-lead update path checks `combined.get("service_interest")`, but `_extract_lead_info` (`:77`) only ever returns `name`/`email`/`phone`. `service_interest` is never a key, so this branch is dead — `areas_of_interest` is never enriched here for existing email-matched leads (the new-lead path uses `_extract_service_interest` separately at `:528`).
- **Impact:** Minor missed enrichment for returning leads; no crash, no data loss.
- **Recommended fix:** Replace with `_extract_service_interest(messages)` to match the new-lead path, or delete the branch.
- **Confidence:** High.

---

## Verified-safe (traced, no action needed)

- **S1 — Appointment double-booking is correctly guarded.** `migrations/005_appointments.sql:44-47` defines `EXCLUDE USING gist (tenant_id WITH =, tstzrange(start,end) WITH &&) WHERE (status='confirmed')` (+ `btree_gist`). `services/booking.py:215` always inserts `status='confirmed'` and the pre-insert overlap SELECT (`:232`) is only a best-effort optimization — the DB constraint is the real backstop. Two concurrent same-slot bookings: both pass the pre-check, both insert, the second raises exclusion → caught at `:257-260` → 409 to caller (`routers/appointments.py:238`). No TOCTOU. (Live-DB application of the constraint not directly queried here; corroborated by `schema-discipline.md` "appointments — Has EXCLUDE constraint.")
- **S2 — Stripe webhook idempotency is robust and shared across both endpoints.** `services/idempotency.py:44` uses an atomic `upsert(on_conflict="key", ignore_duplicates=True)`; the in-flight NULL-body case acks 200 (`:85-90`); `delete_key` releases the row on handler failure so Stripe retries reprocess (GH #308, `:96`). Both `routers/billing.py:236` (`/api/v1/billing/webhook`) and `routers/stripe_webhooks.py:64` (`/api/v1/webhooks/stripe`) call `check_and_record(db, "stripe", event_id)` — a **shared** key namespace — so even if Stripe is configured with both URLs, a given `event_id` is processed once. No double-activation.
- **S3 — Referral reward is idempotent.** `services/referral_reward.py:110` claims the row first via `INSERT` into `referral_rewards` with `UNIQUE(referred_tenant_id)` (migration 162); a duplicate insert is caught and skips the grant (`:134-142`). Never raises (`:266`), gated by kill-switch. Safe against redeliveries and the two parallel endpoints.
- **S4 — Invoice payment is re-check-guarded.** `routers/stripe_webhooks.py:158` re-reads `status` and returns early if already `paid` before updating, on top of S2's dedup.
- **S5 — Widget booking submit blocks double-submit.** `widget/agentnexlify-widget.js:1760` sets `btn.disabled = true` synchronously *before* the first `await` (`:1765`), so a second click can't enter; 409 handled explicitly (`:1782`) with re-enable + return-to-slots.
- **S6 — Automation loop lock is cross-worker and atomic.** `backend/main.py:267` calls RPC `try_acquire_automation_lock`; `migrations/096_production_hardening.sql:111-135` implements it as `INSERT ... ON CONFLICT (name) DO UPDATE ... WHERE locked_until < NOW() OR owner = EXCLUDED.owner` returning `ROW_COUNT > 0` — a correct DB lease. Production fails **closed** (`main.py:286-288`). Only one worker runs each scheduler tick.

---

## Quick wins (low effort, high value)
1. **H1:** add `UNIQUE(client_id, lower(email))` / phone partial indexes + switch capture insert to upsert. Single migration + ~10-line change; kills duplicate leads *and* shrinks M1.
2. **M2:** add `let ignore` guard to `ConversationsPage` load effect (~5 lines).
3. **L2:** one-line `if (loading) return;` in `SignupPage.handleSubmit`.
4. **L3:** swap the dead `service_interest` branch for `_extract_service_interest(messages)`.

## Architectural changes (larger, schedule post-launch if needed)
- **M1:** move new-lead alert dedup from the in-memory `set` to a DB claim via `idempotency_keys` (`provider="lead_alert"`). Do after H1 so the remaining case is rare.
- **L1:** only if a single duplicate weekly email is unacceptable — persist last-sent date. Currently mitigated by S6; likely leave as-is.
- **General:** the codebase already has the right primitives (atomic `idempotency_keys` upsert, DB lease, UNIQUE-claim pattern). The gap is that **lead capture is the one hot mutation path that never adopted them.** Bringing it in line with the Stripe/referral patterns removes the whole H1+M1 cluster.

## Ship recommendation
**Ship-blockable-by-one:** fix H1 (unique index + upsert) before launch — it is the only finding that produces duplicate customer-facing messages and corrupt lead counts under normal single-user traffic; everything else is safe, mitigated, or cosmetic and can land in the first post-launch patch.
