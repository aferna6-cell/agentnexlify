---
paths:
  - "backend/routers/leads.py"
  - "backend/routers/**/*.py"
  - "backend/services/managed_agents_registry.py"
  - "backend/services/advisor_executor.py"
  - "backend/services/os_actions/**/*.py"
---

# Propose-Only for Customer + Financial Records

Council finding #7 (trust). An AI agent must never quietly merge, overwrite, or
delete a customer or financial record. The owner's data is the owner's. When an
agent wants to change it, it proposes; a human approves. When a human takes a
destructive action themselves, it is captured so it can be undone.

## The rule

1. **AI-initiated change to a customer/financial record → propose, never auto-apply.**
   The agent writes a suggestion (a pending row a human reviews), not the record
   itself. This already exists for lead updates: the suggestion path in
   `leads.py` (`/suggestions`) stores the change in `activity_log` and only
   applies it when the owner clicks Approve. New agent write paths follow the
   same shape.

2. **Human-initiated destructive action → allowed, but audited + recoverable.**
   The owner explicitly choosing to merge two duplicate leads is fine — they are
   the actor. But the deleted row must be snapshotted first so the merge can be
   reversed. See `backend/services/record_audit.py`:
   `destructive_snapshot()` captures the full row into `activity_log.metadata`
   before the delete; `find_deleted_snapshot()` reads it back for recovery.

3. **Financial records (invoices, payments, Stripe state) are stricter.** No AI
   write path edits them. A human edits invoices; agents only draft and propose.

## What counts as a customer/financial record

`leads`, `conversations`, `appointments`, `invoices`, `client_notes`,
`documents`, and anything holding PII or money. (`leads`/`conversations` use
`client_id`, not `tenant_id` — see `schema-discipline.md`.)

## When building a new agent action or endpoint that writes these

- Mutating one of the tables above on the AI's initiative → write a suggestion,
  not the record. Mirror the `/suggestions` approve/dismiss flow.
- Deleting or merging on a human's explicit request → call
  `record_audit.destructive_snapshot(table, row, action, related_id)` and pass
  it as `metadata=` to `log_activity` BEFORE the delete.
- Bulk operations (`/bulk-update`) initiated by the owner are allowed; if a bulk
  op deletes rows, snapshot each one.

## What is fine (not destructive, no proposal needed)

- Appending a note, activity-log entry, or message.
- Updating a lead's `status`/`lead_score` from a deterministic rule the owner
  configured (scoring, stage automation).
- Reading/enriching without overwriting owner-entered fields.

## Anti-patterns

- An agent auto-merging "duplicate" leads it detected. Propose the merge; the
  owner confirms which record wins.
- Overwriting an owner-entered field (name, phone) with an AI guess. Fill only
  blank fields, or propose the change.
- Deleting a row with no snapshot. There is no undo without the snapshot.

## Cross-refs
- `backend/services/record_audit.py` — snapshot + recovery helper
- `backend/routers/leads.py` `/merge`, `/suggestions` — reference flows
- `.claude/rules/schema-discipline.md` — client_id vs tenant_id
- `docs/dev-knowledge/council-fixes-register.md` — issue #7
