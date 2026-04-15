# Prompt Formula — ROLE + TASK + CONTEXT + CONSTRAINTS + OUTPUT

## Rule
Non-trivial prompts follow the 5-part formula. Matches cheat sheet (Suryansh Tiwari) + our existing PROMPTLIBRARY schema.

## Formula
```
[ROLE]:        Who executes (persona, seniority, domain)
[TASK]:        Imperative — what to do
[CONTEXT]:     Background, data, file paths, constraints from environment
[CONSTRAINTS]: Hard limits — time/space complexity, style, no-deps, must-use X
[OUTPUT]:      Shape of deliverable — code+tests, markdown doc, JSON, review
```

## Example (from cheat sheet)
```
[ROLE]:        Senior Software Engineer
[TASK]:        Write efficient sorting function
[CONTEXT]:    Working with large datasets (>1M rows)
[CONSTRAINTS]: Time complexity must be O(n log n)
[OUTPUT]:      Python code + unit tests
```

## Map to PROMPTLIBRARY schema
| Cheat sheet | PROMPTLIBRARY.md field | Notes |
|-------------|------------------------|-------|
| ROLE | `**Role:**` | 1:1 match |
| TASK | `**Task:**` | 1:1 match |
| CONTEXT | `**Context:**` | 1:1 match |
| CONSTRAINTS | embed in Context "Guardrails:" section | no separate field |
| OUTPUT | `**Format:**` | 1:1 match |
| — | `**Tone:**` | project-specific (caveman default) |

`CONSTRAINTS` lives inside `Context` → "Guardrails:" sub-section. See existing prompts in `PROMPTLIBRARY.md` for examples.

Optionally add `**Constraints:**` as its own field when hard limits warrant separation (e.g. perf bounds, forbidden libs, max LOC).

## Power-prompt templates (from cheat sheet)
**Build feature:**
> `[ROLE] Senior fullstack. [TASK] Create user authentication flow. [CONTEXT] FastAPI backend + React frontend, Supabase auth, existing JWT middleware in backend/dependencies.py. [CONSTRAINTS] Use client_id not tenant_id. No new deps. No __future__ annotations in FastAPI files. [OUTPUT] Migration + backend routes + frontend page + tests.`

**Debug system:**
> `[ROLE] Senior debugger. [TASK] Investigate memory leak. [CONTEXT] Backend process grows 200MB/hr, baseline 400MB, reproducible in staging. [CONSTRAINTS] No prod restart, reproduce locally first. [OUTPUT] Root cause + minimal fix + regression test.`

**Analyze repo:**
> `[ROLE] Staff engineer onboarding. [TASK] Understand overall architecture. [CONTEXT] Multi-tenant SaaS, FastAPI + React + Supabase. [CONSTRAINTS] Max 3 hrs, summary only. [OUTPUT] Markdown brief: layers, key flows, risk areas.`

## Pro mode template
For high-stakes tasks, layer the "expert system architect" framing:
```
You are an expert [DOMAIN] architect. Analyze [SYSTEM]. Identify
potential bottlenecks in [COMPONENT] using [METHOD]. Recommend
[SCALE] improvements. Provide code examples and performance
rationale. Maintain existing [API/contract/invariants].
```

## When NOT to use
- Trivial asks (rename, typo, one-liner) — direct prompt fine
- Exploratory questions — "what is X" doesn't need formula
- Live iteration on already-running task — too much ceremony

## Cross-refs
- `PROMPTLIBRARY.md` — 13 canonical prompts using this schema
- `.claude/rules/prompt-library.md` — enforcement rule
- Source: Claude Code Master Cheat Sheet v1.0 (Suryansh Tiwari)
