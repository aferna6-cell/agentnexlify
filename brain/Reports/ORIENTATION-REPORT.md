---
type: report
report: orientation
phase: orientation
date: 2026-06-22
status: awaiting-user-approval
---

# Orientation Report — Compiled Vault Brain

Phase 1 (Orientation) output. No ingestion or canonical authoring has happened yet.
This report ends at **Hard Checkpoint 1**: it asks the user whether to proceed.

## 1. Confirmed Working Directory

- **Current working directory:** `/home/user`
- Verified via `pwd` on 2026-06-22.
- `/home/user` is **not** itself a git repo. It contains two git repos:
  - `/home/user/agentnexlify` (branch `claude/agent-nexlify-testing-28d597`)
  - `/home/user/Agent-Nexlify-OS`

## 2. Intended Output Root

- **Output root:** `/home/user/Compiled-Vaults/compiled-vault-brain-2026-06-22/`
- No output root was supplied, so the prompt default is used (under cwd).
- This path is **outside** both git repos, so the vault will not pollute either repo.
- **Durability caveat:** this is an ephemeral remote-execution container. Anything not
  committed/exported before the container is reclaimed is lost. Persistence options are
  raised in the checkpoint questions below.

## 3. Source Inventory (local filesystem)

High-signal, source-of-truth material already on disk (primary source for V1 of the brain):

| Source | Path | Signal |
|---|---|---|
| Product README | `agentnexlify/README.md` | What AgentNexLiFy is |
| Agent OS README/specs | `Agent-Nexlify-OS/README.md`, `Agent-Nexlify-OS/docs/` | Sister product; merged into agentnexlify 2026-06-09 |
| Project rules / onboarding | `agentnexlify/CLAUDE.md`, `agentnexlify/AGENTS.md` | Architecture, invariants, plan/pricing facts |
| Knowledge base wiki | `agentnexlify/knowledge-base/wiki/` (8 categories), `INDEX.md` (47KB), `HOT.md` | 117 compiled articles (competitors, ai-llm, verticals, growth, regulations, technical, small-biz-saas) |
| Dev knowledge | `agentnexlify/docs/dev-knowledge/` | architecture-decisions, bug-patterns, schema-log, failed-approaches, canonical-schema, vertical simulations |
| Engineering memory | `agentnexlify/docs/engineering-memory/` | state, lessons-learned, decisions, blocked-items, progress-tracker, sessions |
| AI memory (JSON) | `agentnexlify/ai/memory/` | architecture_patterns, refactor_patterns, task_history, bug_patterns |
| Planning | `agentnexlify/planning/` | decisions/, architecture/, backlog/, specs/, managed-agents/, positioning + stress-test docs |
| Specs / Plans / Audits | `agentnexlify/specs/` (20), `plans/` (9), `audits/` (27) | Feature specs, implementation plans, architecture audits |
| Docs (broad) | `agentnexlify/docs/` (~40 files) | runbooks, routing, marketing, sales demo, legal, ops |

No pre-existing Obsidian vault was found anywhere under `/home/user`.

## 4. Connector Inventory + Account/Workspace Verification

Read-only identity checks were run (Connector Verification Gate). Full detail is in
`../SOURCE-MANIFEST.md`. Summary:

| Connector | Account / Workspace | Verified via | Status |
|---|---|---|---|
| GitHub | user `aferna6-cell` (id 228568372) | `get_me` | ✅ verified, read OK |
| Vercel | team `aferna6-cell's projects` (`team_nKtxgUlI3JosDKSTsOs3yF96`) | `list_teams` | ✅ verified, read OK |
| Supabase | org **`VoltOps`** (`jsymlqyawvukrxtcoiqz`); projects: `aferna6-cell's Project` (ACTIVE), `agentnexlify-os-demo` (INACTIVE), `BetBrain` (INACTIVE) | `list_organizations`, `list_projects` | ✅ verified, read OK |
| Slack | `aidanfernandes31@gmail.com` (`U0AU23Y8PSN`), workspace **"Agent Nexlify"** | `slack_read_user_profile` | ✅ verified, read OK |
| Google Calendar | **`aferna6@g.clemson.edu`** (Clemson student account) | `list_calendars` | ⚠️ verified, identity differs (see §5) |
| Gmail | address not directly exposed; user-label references `afernandes@hamdenhall.org` | `list_labels` | ⚠️ unconfirmed address — needs header check or user confirm before ingest |
| Google Drive | unknown — read **denied at MCP layer (requires approval)** | `list_recent_files` → "requires approval" | ⛔ BLOCKED pending approval |

## 5. Identity Finding (the reason the verification gate exists)

The connectors span **three distinct identities** belonging to one person, **Aidan Fernandes**:

1. **Builder/dev identity** — GitHub `aferna6-cell`, Vercel `aferna6-cell's projects`,
   Supabase org `VoltOps`. This is the AgentNexLiFy engineering surface.
2. **Personal identity** — Slack `aidanfernandes31@gmail.com` (workspace "Agent Nexlify").
   This matches the session `userEmail`. Treated as the **canonical owner identity**.
3. **Student identity** — Google **Calendar** is `aferna6@g.clemson.edu` (Clemson
   University). Calendars present: a fraternity ("Active Brother Class Schedule"), a campus
   ministry ("LUCU EVENTS"), and the student inbox. Gmail carries a legacy label for
   `afernandes@hamdenhall.org` (a prep school), "Moved 2023-05-17".

**Implication:** The Google connectors (Calendar, Gmail, Drive) are attached to the user's
**student/personal Google identity**, not the AgentNexLiFy business. That is not necessarily
"wrong" — but it means email/calendar ingestion would pull **school + fraternity + personal**
content, which may or may not belong in a "brain." This is a scope decision for the user
(see checkpoint question 2). Until confirmed, Google connectors are **not approved for
ingestion**; Drive is hard-blocked.

## 6. Initial High-Signal Entities (candidates, not yet authored)

Derived from local sources only; to be promoted to canonical notes after approval.

- **People:** Aidan Fernandes (owner/user).
- **Companies/Orgs:** AgentNexLiFy (the business), VoltOps (Supabase org), Clemson University,
  Lambda/fraternity ("Active Brother"), LUCU (campus ministry), Hamden Hall (prep school).
- **Products:** AgentNexLiFy (AI front-desk widget + dashboard), Agent OS / Agent-Nexlify-OS
  (orchestrator + department-head agents; merged into prod 2026-06-09), BetBrain (separate
  Supabase project — unverified scope).
- **Projects:** widget, backend (FastAPI), frontend (React/Vite), agent-service, knowledge-base
  compiler, issue-to-PR autopilot, marketing automation (Draft, deferred per user).
- **Topics:** multi-tenant SaaS, lead capture, Stripe billing/plans (`chatbot` $19.99 /
  `agent_os` $99.99), Claude model routing, RLS/tenant isolation, vertical knowledge bases.
- **Decisions:** Agent OS prod merge (2026-06-09), plan repricing (2026-06-15), agent-os
  graph memory (planning/decisions/2026-05-25), `client_id` not `tenant_id` invariant.
- **Procedures:** migration workflow, widget byte-identical sync, compound-engineering pipeline,
  deploy checks, daily routines.

## 7. Proposed Ingestion Plan (for approval)

**Phase A — Local-first (recommended, low-risk, no connectors):**
Build the canonical brain from the on-disk repos (README, CLAUDE.md, knowledge-base wiki,
dev-knowledge, engineering-memory, planning/decisions, specs/plans/audits). This is the
densest, already-curated, non-sensitive source. Produces People/Companies/Products/Projects/
Topics/Decisions/Procedures/Preferences/Context-Packs/Maps with full provenance to
`Sources/` traces that cite repo file paths.

**Phase B — Connectors (only after explicit per-connector approval):**
- GitHub (read): issues/PRs/commits for decisions + open loops — same identity, low-risk.
- Supabase (read): schema/table inventory for the Products/Topics notes — read-only.
- Slack (read): "Agent Nexlify" workspace smoke pass (5–10 high-signal threads).
- Gmail/Calendar/Drive: **deferred** pending the identity-scope decision (question 2) and,
  for Drive, an approval to read at all.

**Compiler process per item:** parse → group → classify → extract → canonicalize → rehydrate
provenance → author → validate links → critic/audit. Cheap model for parse/classify/extract,
strongest model for synthesis/critic/ambiguous entity resolution.

## 8. Blockers

1. **Google Drive** read is denied at the MCP layer (requires approval). Blocked until approved.
2. **Google identity scope** (Calendar/Gmail = Clemson/personal): need user decision on whether
   school/fraternity/personal content belongs in the brain before any Google ingestion.
3. **Gmail account address** not positively confirmed (only inferred from a label). Needs a
   one-thread header check or user confirmation before ingestion.
4. **Durability**: ephemeral container — vault must be committed/exported to persist.

## 9. Status

Scaffold created (all required folders + `state.json`, `INGESTION-LOG.md`, `SOURCE-MANIFEST.md`,
stub `VALIDATION-REPORT.md`, stub `COMPLETION-AUDIT.md`, `README.md`). **No canonical entity
notes authored yet.** Awaiting user approval at Hard Checkpoint 1.
