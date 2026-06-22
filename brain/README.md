---
type: readme
date: 2026-06-22
status: live
home: agentnexlify/brain
---

# Compiled Vault Brain — Aidan Fernandes

An Obsidian-compatible vault that acts as a durable, source-backed context layer for LLMs
and agents. **Status: live.** Lives at `agentnexlify/brain/` (committed to the repo). Scope:
the AgentNexLiFy business/builder identity (personal/student excluded).

## Agents: start here
Any AI agent working in this repo should **read `Maps/Home.md` first**, then follow wikilinks.
`CLAUDE.md` + `AGENTS.md` at the repo root point here. Treat only source-backed claims as fact
(check each note's `## Provenance`). Never perform external writes without explicit approval.

## Tooling (`_tools/`)
- `run_all.py` — run every validator (links, slugs, secrets, provenance, artifacts, manifest).
- `refresh_connectors.py` — re-sync GitHub + Supabase into the connector source traces (env creds, read-only).
- `export_graph.py` — emit `_index/graph.json` + a self-contained `_index/viewer.html` graph.
- `embed_notes.py` + `ask.py` — build a local Voyage embedding index and ask the brain questions.

Keep current: `brain/_tools/refresh_connectors.py` runs daily via the repo's
`.github/workflows/refresh-brain.yml` (set repo secret `SUPABASE_ACCESS_TOKEN`). See
`Procedures/Refresh The Brain.md`.

## How this vault is organized

| Folder | Memory type | Holds |
|---|---|---|
| `People/` | declarative | canonical person notes |
| `Companies/` | declarative | organizations |
| `Projects/` | declarative | active/past work efforts |
| `Products/` | declarative | products & systems |
| `Topics/` | declarative | concepts, domains |
| `Decisions/` | declarative | decisions w/ rationale + consequences |
| `Commitments/` | declarative | open loops, promises, TODOs |
| `Procedures/` | procedural | how-to / repeatable processes |
| `Preferences/` | procedural | user preferences & patterns |
| `Context Packs/` | runtime | task-scoped bundles for agents |
| `Sources/` | source traces | provenance records (one per source item) |
| `Maps/` | indexes | MOCs / dashboards linking the above |
| `Reports/` | meta | orientation + status reports |
| `_tools/` | machinery | validation scripts |

Root files: `SOURCE-MANIFEST.md` (connectors + sources), `VALIDATION-REPORT.md` (script
results), `COMPLETION-AUDIT.md` (requirement→evidence map), `INGESTION-LOG.md` + `state.json`
(resumable state).

## How agents should use it

1. Start from `Maps/` or a relevant `Context Packs/` note.
2. Treat only **source-backed** claims as facts; check the `## Provenance` section and
   `SOURCE-MANIFEST.md` for freshness.
3. Do not assume facts not present in linked notes. Represent uncertainty explicitly.
4. **Never perform external writes/mutations** (email, messages, calendar, DB writes,
   billing) without explicit user approval.

## Provenance model

Every promoted canonical note has a `## Provenance` section linking to one or more
`Sources/<id>` traces. Source traces point at the underlying repo file, connector record,
or document — never at raw secrets.

## Validation

Deterministic scripts live in `_tools/` (wikilinks, slugs/paths, secret scan, provenance,
required-artifacts, manifest). Results are recorded in `VALIDATION-REPORT.md`. The vault is
not declared complete until all hard gates pass.
