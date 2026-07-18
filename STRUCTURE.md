# Repo Structure — 4-Folder Convention

> Zero ambiguity for agents. Source: @kloss "Structure your repos. Your agents will thank you."

Four root folders, four roles. Agents stop guessing what files mean.

| Folder | Role | Verb | Contents |
|--------|------|------|----------|
| **`/audits`** | Proof | verify | Audit reports, security scans, dependency reports, code reviews, performance benchmarks, post-mortems |
| **`/docs`** | Description | describe | What things ARE — API references, dev knowledge, architecture diagrams, glossaries, codemaps, daily logs |
| **`/plans`** | Intent | plan | What we INTEND to do — phased implementation plans, sprint plans, refactor plans, rollout plans |
| **`/specs`** | Law | enforce | Binding contracts — feature specs, PRDs, acceptance criteria, success metrics. Specs are authoritative |

## How agents use this

| Agent question | Lookup folder |
|----------------|---------------|
| "Is this feature done correctly?" | `/audits` (proof of verification) |
| "What does X mean?" | `/docs` (definitions) |
| "What's the next step on Y?" | `/plans` (sequenced intent) |
| "What MUST this feature do?" | `/specs` (the law) |

## Naming
- Audits: `audit-<topic>-YYYY-MM-DD.md` (e.g. `audit-dependency-2026-04-15.md`)
- Docs: `<topic>.md` (e.g. `glossary.md`, `api-reference.md`)
- Plans: `<feature>_plan.md` (e.g. `lead-scoring-v2_plan.md`)
- Specs: `<feature>_spec.md` (e.g. `lead-scoring-v2_spec.md`)

## What lives where (worked examples)

```
/audits/audit-security-2026-04-15.md      ← security scan output
/audits/audit-dependencies-2026-04-15.md  ← npm + pip CVE scan
/audits/audit-codebase-health-2026-04.md  ← health-check skill output

/docs/glossary.md                          ← canonical term list
/docs/api/leads.md                         ← API reference
/docs/dev-knowledge/bug-patterns.md        ← bug postmortem catalog
/docs/CODEMAPS/                            ← architecture maps

/plans/onboarding-wizard_plan.md           ← phased rollout
/plans/dashboard-rebuild_plan.md           ← migration plan

/specs/onboarding-wizard_spec.md           ← what it MUST do
/specs/full-dashboard-buildout_spec.md     ← acceptance criteria
```

## Companion skills
- `write-prd` outputs to `/specs/`
- `prd-to-plan` outputs to `/plans/`
- `dependency-auditor` outputs to `/audits/`
- `api-docs-generator` outputs to `/docs/api/`
- `triage-issue` files GH issues, not local — but root cause goes to `/audits/postmortems/`
- `edit-article` edits `/docs/` and `/specs/`
- `ubiquitous-language` outputs to `/docs/glossary.md`

## Workflow folders (NOT covered by 4-folder rule)
These exist for process, not artifacts:
- `/planning` — workflow context, decisions/, architecture/, managed-agents/ (process state)
- `/.claude` — Claude Code config (skills, agents, commands, hooks)
- `/scripts` — automation
- `/migrations` — DB migrations (numbered)
- `/backend`, `/frontend`, `/widget` — code

## Why this matters
Most repos dump .md files into `/docs` or root. Agents (Claude Code, Codex, Cursor) hallucinate context because they can't tell intent from law from description from proof.

This convention separates them. Agents stop guessing.

## Migration log
- 2026-04-15 — Created `/audits`, `/specs`, `/plans` at root. Moved `planning/specs/` → `/specs/`. Kept `planning/` for workflow state (decisions/, architecture/, CONTEXT.md). 2026-07-18 — finished that move: deleted the stale `planning/specs/` stragglers, relocated `lead-parser-replacement_spec.md` to `/specs/`.
