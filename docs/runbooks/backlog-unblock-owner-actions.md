# Runbook — Unblock the Backlog (Owner Actions)

Every open backlog item that is *not* code-completable is gated on a small set
of owner-only actions: applying migrations, setting secrets, or submitting
external apps. This runbook is the executable checklist for those actions,
cross-linked to the issues each one unblocks. Nothing here can run from the
agent/CI environment (no Supabase write access, no prod secrets, no external
accounts); all of it is fast for the owner.

Last compiled: 2026-07-22. Source: session backlog sweep + morning digest #538.

---

## 1. Apply the staged migrations (Supabase) — DONE (verified 2026-07-22)

**All applied and verified against prod.** `list_migrations` on the active
project (`pxserpybmajixqrmzaly`) shows every migration through 186; a targeted
`information_schema` + `pg_indexes` check confirmed the columns, constraints,
indexes, and the `increment_kb_citations` RPC all exist. No action remains here.

| Migration | Unblocks | Verified live |
|---|---|---|
| `180_os_scheduled_tasks.sql` | Agent OS recurring tasks | `os_scheduled_tasks` table present |
| `181_kb_article_provenance.sql` | #70 KB provenance | `kb_articles.last_validated` + `citation_count` + `increment_kb_citations` RPC |
| `182_conversation_message_memory.sql` | #69 conversation memory | `chat_messages.message_confidence`/`_relevance_score` + partial index |
| `185_photo_quote_feedback.sql` | #44 photo-quote telemetry | `quote_requests.tenant_feedback` + `led_to_appointment` |
| `186_pending_automations.sql` | #118 retry queue | `pending_automations` table + status CHECK + due/tenant indexes |

The missed-call SMS / GCal-sync retry drainer
(`backend/services/retry_worker.py`, wired into the 60s automation loop) is now
live against the real `pending_automations` table.

---

## 2. Set the secrets

### `INTEGRATIONS_ENC_KEY` (Railway prod + GitHub Actions) — unblocks #536, #266
A `cryptography.fernet` key. Without it the integration key vault fails closed
and the OAuth-token encryption stays half-done.
1. Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
2. Set `INTEGRATIONS_ENC_KEY` in Railway prod env vars and as a GitHub Actions secret.
3. Smoke-test a new OAuth connect (Google Drive or Calendar) end to end.
4. Run the backfill: `python scripts/backfill_integration_encryption.py --dry-run`,
   then live. Confirm `access_token_enc` is populated for every row with a
   non-null plaintext token.
5. Only after 1-4 are verified in prod: write + apply the sunset migration that
   drops the plaintext `integrations.access_token` / `refresh_token` columns
   (#266 step 4). **Do not write this migration before the backfill is verified
   — the plaintext columns are the only token copy until the enc columns are
   populated.**
6. Close #536, then #266.

### `ANTHROPIC_API_KEY` + `SUPABASE_ACCESS_TOKEN` (GitHub Actions) — unblocks #403
Nightly KB compile + autopilot jobs need these. Rotate/set in
Settings → Secrets → Actions. Then re-run the nightly workflow to clear the KB
staleness alert.

### `AUTOPILOT_GH_TOKEN` (GitHub Actions) — unblocks #399
Expired 18+ days per digest #538; 30+ `ai-ready` issues are stalled from the
issue-to-PR loop. Regenerate the PAT, update the secret, re-run the loop.

### `SUPABASE_SERVICE_KEY` → service_role (GitHub Actions) — unblocks #484
The current value behaves like an anon key (RLS returns zero tenant rows), so
every daily-digest / loop-health job is blind. Rotate the Actions secret to the
Supabase **service_role** key.

### `REFERRAL_REWARD_ENABLED=1` (env) — unblocks #413
Referral flow is built but not live; set the flag to enable it.

---

## 3. External app submissions

### Zapier public app — unblocks #61, and the #60 dashboard deep-link
The CLI app code ships in `zapier/` (auth + `new_lead` polling trigger, syntax +
structure verified). Owner steps (need a Zapier developer account; see
`zapier/README.md` for the full checklist):
1. `cd zapier && npm install && npm install -g zapier-platform-cli`
2. `zapier login`, `zapier register "AgentNexLiFy"`
3. `zapier validate` → `zapier test` (with a real API key from the dashboard)
4. Upload logo + screenshots; `zapier push` (private beta, 5 testers)
5. `zapier promote <version>` → 2-4 week Zapier review
6. After promotion, set `ZAPIER_APP_URL` in
   `frontend/src/pages/IntegrationsZapierPage.jsx` to the published deep-link —
   the dashboard "Connect to Zapier" button activates automatically.

### Google OAuth consent (Drive KB) — GA gate for the drive-kb epic (#56)
Publish the Google Cloud OAuth consent screen with the sensitive
`drive.readonly` scope (may require Google verification). The backend
(`kb_integrations.py`) + `INTEGRATIONS_ENC_KEY` (section 2) are the code/secret
prerequisites.

### Google Business Profile OAuth (review responder) — unblocks #451
`backend/services/review_responder.py::post_response_stub` implements the GBP
`accounts.locations.reviews.updateReply` call once GBP OAuth credentials are
configured. Blind implementation was intentionally deferred (unverifiable
external API contract).

---

## 4. Owner decisions (no code until decided)

| Issue | Decision needed |
|---|---|
| #217 | Stripe Connect self-serve — depends on the billing-architecture direction |
| #330 | Human legal review of the rewritten TermsOfService section 4 (payments) |
| #415 | Keys Koffee tenant — add business hours to enable booking (data entry) |
| #33 | Managed Agents production rollout plan (GTM / pricing / capacity) |
| #500 | GitHub Actions down repo-wide — hosted-runner / billing remediation |

---

## 5. Deferred-by-design (intentionally not started)

Leave open; these have explicit gates. #46 (photo-quote v2 multi-image — "do not
start until error rate <5% held 30 days"), #55 (drive-kb Dropbox/OneDrive/Box —
post-GA), #63 (zapier OAuth + dynamic fields — needs Zapier partner tier), #193
(subconscious moratorium), #265 (re-raise the `fastapi<0.136` cap only once
`starlette` is bumped past 0.49.x — re-raising now re-introduces the CI-proven
zero-routes bug).

---

## Sequence recommendation

1. ~~Migrations (section 1)~~ — DONE, verified applied 2026-07-22.
2. Secrets first (section 2) — cheapest, unblocks the most (#536/#266, #403,
   #399, #484, #413).
3. Zapier + Google submissions (section 3) — long external lead times, start early.
4. Owner decisions (section 4) — as bandwidth allows.
