# Data Processing Addendum (DPA) — AgentNexLiFy

> **Template for customers who ask** (launch rubric 1.8). This DPA is
> incorporated into the AgentNexLiFy Terms of Service when executed by both
> parties. NOT LEGAL ADVICE — have counsel review before first execution
> with a customer. Bracketed fields are filled per customer.

**Effective date:** [DATE]
**Customer ("Controller"):** [CUSTOMER LEGAL NAME]
**Provider ("Processor"):** [AGENTNEXLIFY LEGAL ENTITY] ("AgentNexLiFy")

## 1. Scope and roles

This Addendum governs AgentNexLiFy's processing of Personal Data on the
Customer's behalf through the AgentNexLiFy service (embedded chat widget,
Agent OS assistants, lead management, appointment booking, messaging
automation). Customer is the data controller for its end customers' Personal
Data; AgentNexLiFy is the data processor. For AgentNexLiFy's own account
data about the Customer (login email, billing), AgentNexLiFy is an
independent controller per its Privacy Policy.

## 2. Categories of data and data subjects

- **Data subjects:** the Customer's end customers, leads, and staff.
- **Personal Data processed:** names, email addresses, phone numbers,
  appointment details, conversation content submitted through the chat
  widget or inbound channels (email/SMS/social messaging), invoice and quote
  details, and facts the Agent OS memory extracts from the Customer's own
  conversations with its assistants.
- **Special categories:** the service is not designed for them; Customer
  agrees not to direct special-category data into the service.

## 3. Processing instructions

AgentNexLiFy processes Personal Data only: (a) to provide the service as
configured by the Customer (including AI-generated drafts and, where the
Customer enables auto-send, AI-sent communications); (b) per the Customer's
documented instructions; and (c) as required by law, in which case
AgentNexLiFy informs the Customer unless legally barred.

## 4. Subprocessors

Customer authorizes these subprocessors; AgentNexLiFy gives 30 days' notice
before adding or replacing one (objection right within that window):

| Subprocessor | Purpose | Location |
|---|---|---|
| Supabase (PostgreSQL hosting) | Primary data store | USA |
| Railway | Application hosting | USA |
| Vercel | Dashboard/site hosting | USA |
| Anthropic | AI model inference (Claude) | USA |
| Stripe | Payments | USA |
| Twilio | SMS/voice delivery | USA |
| Resend | Email delivery | USA |
| Voyage AI | Text embeddings (semantic memory) | USA |

AI inference note: conversation content is sent to Anthropic to generate
responses. Per Anthropic's commercial terms, API inputs/outputs are not used
to train models.

## 5. Security

AgentNexLiFy maintains appropriate technical and organizational measures,
including: per-tenant data isolation enforced at the query layer and via
Postgres row-level security; encryption in transit (TLS) and at rest
(provider-managed); API keys transmitted in request bodies (never URLs or
logs); webhook signature verification on all inbound integrations; secrets
in environment configuration, never source control; rate limiting on
authentication and destructive endpoints; and an incident-response playbook
(`docs/incident-response-playbook.md`).

## 6. Confidentiality

Persons authorized to process Personal Data are bound by confidentiality
obligations.

## 7. Data subject rights assistance

AgentNexLiFy assists the Customer in responding to data subject requests:
- **Access/export:** Customer can export leads, conversations, and
  appointments from the dashboard, or request a structured export.
- **Deletion:** Customer-initiated deletion of individual records via the
  dashboard; full account erasure via the self-serve deletion endpoint
  (`POST /api/v1/account/delete`), which purges all tenant data, AI memory
  (semantic entries and knowledge-graph nodes/edges), and billing linkage.
- **AI memory:** the Agent OS Memory panel lets the Customer view and delete
  any individual fact or entity the system has learned ("Forget").

## 8. Deletion and return

On termination, AgentNexLiFy deletes the Customer's Personal Data within 30
days of a deletion request (immediately on use of the self-serve endpoint),
except where retention is legally required (e.g., billing records). Backups
expire on the storage provider's rotation schedule (currently daily backups,
provider-managed retention).

## 9. International transfers

Data is processed in the United States. Where Customer transfers EU/UK
personal data, the parties incorporate the EU Standard Contractual Clauses
(Module 2: controller → processor) and the UK Addendum by reference, with
the Annexes deemed completed by Sections 2, 4, and 5 of this DPA.

## 10. Audits

On reasonable written notice (max once per year, absent a security
incident), AgentNexLiFy will make available information reasonably necessary
to demonstrate compliance with this DPA, which may be satisfied by summaries
of third-party hosting providers' audit reports (e.g., SOC 2 reports of
Supabase/Stripe/Anthropic).

## 11. Breach notification

AgentNexLiFy notifies the Customer without undue delay (target: within 72
hours of confirmation) after becoming aware of a Personal Data breach
affecting the Customer's data, with the information reasonably needed for
the Customer's own notification obligations.

## 12. Liability and order of precedence

Liability follows the limitations in the Terms of Service. If this DPA
conflicts with the Terms, this DPA controls for data-protection matters.

---

**Customer:** ______________________  Date: ________
**AgentNexLiFy:** ______________________  Date: ________
