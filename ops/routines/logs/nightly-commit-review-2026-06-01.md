# Nightly Commit Review — 2026-06-01

## Commits reviewed (last 24h)

| SHA | Message | Risk |
|-----|---------|------|
| `608c010` | subconscious: run 2026-05-31-pm (run 43) — Extend AUTONOMOUS-EXECUTABLE scope | LOW |
| `00fc2af` | subconscious: run 2026-05-31 (run 42) — De-couple Item A as AUTONOMOUS-EXECUTABLE | LOW |
| `2c15688` | ops: nightly-commit-review 2026-05-31 | LOW |

All 3 commits touch `subconscious/` governance files and `ops/routines/logs/` only. No production code changed. No bugs found.

## Findings

### Fixed autonomously (1 fix, 2 files)

- [LOW] Em-dash in comments → replaced with hyphens
  - `frontend/src/utils/api/os-inbound.js:2,5,6` — JSDoc comment em-dashes
  - `frontend/src/components/App.jsx:339,350` — inline comment em-dashes
  - Commit: see `fix(nightly): em-dash in comments [auto-nightly-2026-06-01]`

### AUTONOMOUS-EXECUTABLE executed (1 item)

- [RUN 43 WINNER] Updated `.claude/skills/nightly-commit-review/SKILL.md`
  - Added bash additions to `scripts/hooks/pre-commit` to LOW autonomous scope
  - Added Item A inline patch + pre-condition check requirement
  - Commit: see `docs(skill): extend nightly autonomous scope for pre-commit bash additions [auto-nightly-2026-06-01]`

### Issues opened (2)

- **GH #194** [MEDIUM] Em-dash violations in UI copy blocking Item A
  - 5 violations in 3 JSX files (`IntegrationsPage`, `SettingsInboundChannels`, `MessagingSettingsCards`)
  - Product decision required: replace with hyphens OR scope check to skip .jsx/.tsx
  - Blocks: Item A (check_project_invariants.py pre-commit wiring)

- **GH #193** [MORATORIUM] Comment added — 14 pending, oldest day 46

### Item A status: BLOCKED

`check_project_invariants.py` fails (exit 1) on 5 UI em-dash violations. Wiring as blocking pre-commit would break all commits. Pre-condition check added to SKILL.md — Item A will execute automatically next nightly run after script passes clean.

### Skipped

- No commits touched FORBIDDEN paths (migrations, auth, stripe, widget)

## Moratorium Status

- `moratorium_active: true` — day 29+
- `runs_pending_approval: 14`
- `oldest_pending: 2026-04-16` — day 46
- Escalation criteria met (>3 pending, >14 days) → comment added to GH #193

## Guardrails check

| Guardrail | Status |
|-----------|--------|
| Max 5 files | PASS (2 files fixed) |
| Max 50 LOC | PASS (~5 lines changed) |
| No test modifications | PASS |
| No FORBIDDEN paths | PASS |
| CLAUDE.md invariants respected | PASS |

## Next action

1. Resolve GH #194 (em-dash in UI copy) → Item A executes autonomously next nightly
2. Resolve GH #181 (billing constants) — Check 11 fires WARNING on every commit
3. Human: `/moratorium-sprint` to clear sprint items and exit moratorium
