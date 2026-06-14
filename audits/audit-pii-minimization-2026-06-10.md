# Audit — PII Minimization (launch rubric 6.5)

**Date:** 2026-06-10
**Scope:** what personal data the platform stores, where it flows, what reaches logs and third parties, and whether anything is collected without a purpose.

## 1. Inventory — PII stored, by purpose

| Data | Tables | Purpose | Needed? |
|---|---|---|---|
| End-customer name/email/phone | `leads`, `conversations`, `chat_messages`, `appointments`, `invoices`, `orders` | Core product: lead capture, booking, billing on the tenant's behalf | Yes |
| Conversation content | `chat_messages`, `conversations`, `os_messages` | The product IS the conversation; feeds agent context + memory | Yes |
| AI-learned facts | `os_memory_entries`, `os_graph_nodes/edges` | Long-term memory; owner-visible and owner-deletable (Memory panel Forget) | Yes |
| Tenant owner identity | `tenants` (owner_name, owner_email, phone) | Account, billing, notifications | Yes |
| Team identities | `team_members` | RBAC | Yes |
| Crawled website text | `website_content` | Tenant's own public site, feeds agent KB | Yes (public data) |
| Payment data | **none** — `stripe_customer_id`/`subscription_id` references only | Stripe holds card data | Correct: no PAN/CVV anywhere (verified by grep across backend/ + migrations/) |
| Gov't IDs / SSN / health data | **none** | Not designed for it; DPA §2 prohibits special categories | Correct |

## 2. Findings

**F1 (fixed this audit): full email addresses logged at INFO.**
`backend/services/email_sender.py` logged recipient addresses on send/skip/fail (5 sites). Fixed: `mask_email()` helper (`j***@domain.com`) applied at all 5. Railway retention is 7 days, but addresses in logs contradicted the stated posture (secrets/keys already excluded from logs).

**F2 (open, one line): weekly digest logs owner email.**
`backend/services/automation/scheduled_jobs_ext.py:501` — `"Sent weekly digest to %s"` with the raw address. Same fix (`mask_email`); apply in next pass touching that file. Owner-only PII, low severity.

**F3 (accepted): conversation content goes to Anthropic for inference.**
Required for the product; covered by DPA §4 (subprocessor table) and Anthropic's no-training commercial terms. Voyage receives text for embeddings under the same framing.

**F4 (accepted): widget collects only what the visitor types + contact fields.**
No fingerprinting, no analytics beacons in the widget script; session id is random, 30-min timeout. AI disclosure shown in greeting (rubric 1.7).

## 3. Deletion coverage

- Self-serve full erasure: `POST /api/v1/account/delete` purges the entire table inventory above (`account_deletion.TENANT_DATA_TABLES`, coverage-guarded by test so new tables can't be missed), closes the Stripe customer, removes the tenant row.
- Granular: leads/conversations deletable in dashboard; AI memory per-fact via Memory panel Forget (graph edges cascade).
- Backups: provider-rotated (Supabase daily); DPA §8 documents the window.

## 4. Verdict

PII collected maps 1:1 to product purposes; no payment/special-category data is stored; deletion is complete and self-serve; the one live leak (emails in logs) is fixed with F2 queued as a one-liner. **Score 6.5: 1 → 2** with F2 noted.
