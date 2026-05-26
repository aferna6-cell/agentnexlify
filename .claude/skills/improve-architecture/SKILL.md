---
name: improve-architecture
description: "Full structural review of the AgentNexLiFy codebase — file bloat, god classes, layer violations, dead code, dependency rot, schema drift, performance hotspots. Output is a ranked fix list with severity + effort scores. Load when user says 'improve architecture', 'architecture review', 'structural review', 'codebase health', 'refactor plan', '/improve', or asks to audit the codebase structure."
version: 1.0.0
origin: agentnexlify
user-invocable: true
triggers:
  - improve architecture
  - architecture review
  - structural review
  - codebase health check
  - refactor plan
  - /improve
  - audit the codebase
  - technical debt
  - code health
allowed-tools: [Read, Bash, Grep, Glob]
effort: high
---

# Improve Architecture — Full Structural Review

**ultrathink** — architectural review requires deep reasoning across file bloat, layer violations, schema drift, and second-order effects. Do not short-circuit.

Systematic codebase audit. Output is a ranked, actionable fix list. No changes made during this skill — diagnosis only. Hand the output to compound-engineering or individual agents to execute fixes.

## When to Use
- Weekly or before major feature work
- After any large refactor to catch regressions
- When a god class is suspected (file >600 lines)
- Before a release to surface hidden tech debt
- When user says "why is this codebase so hard to work in"

## When NOT to Use
- Mid-feature (finish what you're building first)
- When the ask is already scoped to one file

---

## Pass 1 — File Bloat + God Classes

```bash
# Files >600 lines (God class threshold from user-rules.md Rule 9)
find . -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" \
  | grep -v node_modules | grep -v .venv | grep -v dist | grep -v __pycache__ \
  | xargs wc -l 2>/dev/null | sort -rn | awk '$1>600' | head -20
```

For each file >600 lines:
- List top 3 concerns it handles (single-responsibility check)
- Flag if >1 concern → candidate for split
- Note which concern is "native" vs "squatting"

---

## Pass 2 — Layer Violations

Check for cross-layer imports that shouldn't exist:

```bash
# Routers importing from other routers (should go through services)
grep -r "from backend.routers" backend/routers/ --include="*.py" -l

# Services importing from routers (backwards dependency)
grep -r "from backend.routers" backend/services/ --include="*.py" -l

# Frontend pages importing from other pages (should go through api/ utils)
grep -r "from.*pages/" frontend/src/pages/ --include="*.jsx" --include="*.tsx" -l

# Widget importing backend models directly
grep -r "from backend" widget/ -l 2>/dev/null
```

Flag any hits. Each is an architectural violation.

---

## Pass 3 — Dead Code Candidates

```bash
# Python functions never called (rough heuristic — verify before deleting)
# Exported symbols in backend not imported anywhere
grep -r "^def " backend/ --include="*.py" -h | sed 's/def //' | sed 's/(.*//' \
  | while read fn; do
      count=$(grep -r "$fn" backend/ --include="*.py" -l | wc -l)
      [ "$count" -le 1 ] && echo "CANDIDATE: $fn (only defined, never called elsewhere)"
    done 2>/dev/null | head -20

# Frontend components defined but never imported
grep -r "^export default\|^export const\|^export function" frontend/src/components/ \
  --include="*.jsx" --include="*.tsx" -h | head -30
```

Cross-check candidates with `gitnexus_impact` before flagging as dead.

---

## Pass 4 — Schema Drift

```bash
# Columns referenced in code that may not exist in schema
grep -rn "\.eq(\"" backend/ --include="*.py" | grep -v "client_id\|tenant_id\|id\|status\|created_at\|updated_at" \
  | grep -v "#" | head -20

# Check for old forbidden column names still in code
grep -rn "tenant_id\|lead_stage\|service_interest" backend/routers/ backend/services/ \
  --include="*.py" | grep -v "# " | grep -v "tenant_select\|tenant_table\|tenant_insert"
```

Any hits here are P0 bugs per `schema-discipline.md`.

---

## Pass 5 — Dependency Rot

Invoke `.claude/skills/dependency-auditor/SKILL.md` for full output, then summarize:
- CVE count (critical / high / medium)
- Packages abandoned >2 years
- Packages with available major upgrades
- Estimated upgrade effort (low / medium / high)

---

## Pass 6 — Performance Hotspots

```bash
# N+1 query candidates: loops containing DB calls
grep -n "for.*in\|while " backend/routers/ backend/services/ --include="*.py" -r -A3 \
  | grep -B1 "\.execute()\|supabase\." | head -30

# Missing indexes heuristic: .eq() on non-id columns in hot paths
grep -rn "\.eq(\"" backend/routers/ --include="*.py" \
  | grep -v "\"id\"\|\"client_id\"\|\"tenant_id\"\|\"session_id\"\|\"status\"" | head -20

# Sync calls in async paths
grep -rn "time\.sleep\|requests\." backend/ --include="*.py" | grep -v "test_\|# " | head -10
```

---

## Output Format

After all 6 passes, produce:

```
## Architecture Health Report — <date>

### CRITICAL (fix before next deploy)
- [ ] <item> | Pass <N> | Est effort: <S/M/L>

### HIGH (fix this sprint)
- [ ] <item> | Pass <N> | Est effort: <S/M/L>

### MEDIUM (tech debt backlog)
- [ ] <item> | Pass <N> | Est effort: <S/M/L>

### LOW (nice to have)
- [ ] <item> | Pass <N> | Est effort: <S/M/L>

### Stats
- Files >600 lines: N
- Layer violations: N
- Dead code candidates: N
- Schema drift risks: N
- CVEs (C/H/M): N/N/N
- N+1 candidates: N
```

Save report to `audits/audit-architecture-YYYY-MM-DD.md`.

---

## After the Report

Hand critical/high items to:
- Schema drift → `schema-guard` skill
- God classes → `god-class-splitter` skill for execution (CRITICAL files: invoke immediately, note split axis in `plans/god-class-refactor_plan.md`)
- Dead code → `dead-code-sweep` skill
- Dependencies → `dependency-auditor` skill
- Performance → targeted Sonnet execution with the specific query

Do NOT fix everything in one pass. Prioritize CRITICAL first.

## Bundled Script

`scripts/audit.py` — deterministic structural scan, no LLM calls.

```bash
python .claude/skills/improve-architecture/scripts/audit.py
# → markdown table: god classes, layer violations, dead imports, migration gap
```

## Cross-refs
- `.claude/rules/user-rules.md` Rule 9 — God class threshold (600 lines)
- `.claude/rules/schema-discipline.md` — forbidden column names
- `.claude/skills/dead-code-sweep/SKILL.md`
- `.claude/skills/dependency-auditor/SKILL.md`
- `.claude/skills/compound-engineering/SKILL.md`
