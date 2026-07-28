# Idea 1 — Create `feature-docs-trio` SKILL.md

**Category:** Workflow efficiency  
**Evidence strength:** HIGH — 3 occurrences in 7 days (717c7f3, 14ebe8e, d50d1e8)  
**Execution channel:** nightly commit-review (SKILL.md file creation proven)

## What

Create `.claude/skills/feature-docs-trio/SKILL.md` documenting the pattern observed 3× in 7 days:
After any feature PR merges, produce KB wiki article + ADR entry + INDEX.md update + optional runbook in a single `[skip ci]` commit, within 48h of the feature landing.

## Evidence

From `docs/skill-discovery/2026-07-27.md`:
- `717c7f3` (#45): photo-quote feature → wiki + ADR + INDEX update
- `14ebe8e` (#54): drive-kb integration → wiki + ADR + INDEX + runbook
- `d50d1e8` (#62): zapier integration → wiki + 3 CRM guides + INDEX + runbook

All 3 followed same structure within 2 days of the feature PR merging. Pattern is consistent and repeatable.

## Steps the skill encodes

1. Read closing PR description → extract feature name, decisions, tier gates
2. Write `knowledge-base/wiki/<category>/<feature-name>.md` (Karpathy-style — what, how, tier-gates, failure modes, related wikilinks). Run `npm run kb:lint`.
3. Add ADR entry to `docs/dev-knowledge/architecture-decisions.md` (format: `ADR-YYYY-MM-DD-NNN — <title>` + 2-3 sentence rationale + alternatives rejected)
4. Add entry/entries to `knowledge-base/INDEX.md` under correct category
5. If failure mode on-call must act on: write `docs/runbooks/<feature>-failures.md`
6. Commit as `docs(<feature>): KB article + ADR + runbook [skip ci]`

## Why it matters

The `feature-docs-trio` pattern compounds: every shipped feature that gets documented reduces future Claude context burn (KB articles reduce research time), improves tenant AI quality (more accurate wiki → better widget answers), and creates a runbook trail that accelerates incident response.

Estimated time saved: 30–45 min per feature (eliminating "which sections do I need?" overhead, preventing kb:lint violations, catching missing INDEX entries).

At 2–3 features/week current velocity: 60–135 min/week saved.

## Execution path

Nightly SKILL.md can create skill files. No code changes. No schema changes. Zero risk of customer impact if wrong.

Skill-discovery report already provides the full step details — this is copy-editing, not design work.
