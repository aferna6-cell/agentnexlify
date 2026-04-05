# Agent System Plan

_Last updated: 2026-04-05_

## Purpose
This document defines the intended steady-state for AgentNexLiFy's coding-agent system.

It exists because the repo has grown a powerful agent stack across multiple files and directories, but the control planes drifted:
- `CLAUDE.md`
- `AGENTS.md`
- `.ai/manifest.json`
- `.claude/commands/*`
- `.claude/skills/*`
- `.codex/skills/*`

This plan makes the hierarchy explicit.

## Canonical Hierarchy

### 1. `CLAUDE.md` — canonical human-readable repo brain
Use as the main narrative source of truth for:
- architecture
- schema invariants
- workflow philosophy
- agent inventory
- orchestration expectations
- model-policy narrative

### 2. `.ai/manifest.json` — canonical machine-readable index
Use as the structured source of truth for:
- current agents
- current skills
- current workflows
- directory map
- critical invariants
- model routing policy summary

It should be regenerated/updated whenever the real agent surface changes.

### 3. `AGENTS.md` — thin Codex/general-agent adapter
Use as a short bootstrap for Codex and generic agents:
- read `CLAUDE.md`
- consult `.ai/manifest.json`
- load relevant skills
- follow current model-routing and orchestration defaults

It should not try to duplicate the full repo brain.

## Control Planes

### Core control planes
- `CLAUDE.md`
- `.ai/manifest.json`
- `.claude/settings.json`
- `.claude/commands/*`
- `.claude/skills/*`
- `.codex/skills/*`

### Supporting but non-canonical
- `AGENTS.md`
- tool-specific instruction mirrors (`GEMINI.md`, Copilot instructions, etc.)

### Experimental / optional
- GAN agents
- `build-loop`
- generated skills
- any autonomous loop that is not the default day-to-day path

## Recommended Default Orchestration Path

### Default
Use **`coordinator`** as the default orchestration story for complex work.

Why:
- it is simpler than competing orchestration narratives
- it can delegate to specialized agents cleanly
- it avoids multiple “default” orchestration stories competing for authority

### Supporting workflows
- `delegate` remains useful as a planning entrypoint
- `team-orchestration` remains a reusable skill
- `compound-engineering` remains available for heavier multi-stage tasks

### Explicit non-defaults
- `build-loop` should be labeled experimental / non-canonical
- GAN agents should be labeled experimental / research harnesses

## Agent Classification

### Core implementation team
- `schema-guardian`
- `backend-dev`
- `frontend-dev`
- `widget-specialist`
- `qa-tester`
- `devops`
- `vertical-checker`

### Review / governance team
- `security-reviewer`
- `code-reviewer`
- `tdd-guide`
- `performance-optimizer`
- `refactor-cleaner`
- `architect`

### Experimental / harness
- `gan-planner`
- `gan-generator`
- `gan-evaluator`

## Model Routing Policy

### Codex
Use for:
- implementation
- code surgery
- debugging
- file exploration
- tests and refactors
- day-to-day execution

**Role:** primary execution engine

### Anthropic
Use for:
- canonical repo reasoning
- prompt/system design review
- high-context architecture review
- product-model authority
- customer-facing runtime AI logic

**Role:** canonical repo brain + production AI authority

### MiniMax
Use for:
- cheap summarization
- triage
- lightweight subagents
- lower-stakes synthesis
- orchestration helpers where cost and throughput matter more than exactness

**Role:** lightweight orchestration / summarization engine

## Practical Delegation Guidance

### When editing product/runtime code
Default split:
1. `schema-guardian` if schema-sensitive
2. `backend-dev` and/or `frontend-dev`
3. `widget-specialist` when embed/runtime chat is touched
4. `qa-tester` before done
5. `security-reviewer` for auth/payment/MCP/AI trust boundary work

### When doing strategic/architecture work
Default split:
1. `architect`
2. `security-reviewer` if trust boundaries matter
3. `performance-optimizer` if runtime-critical
4. `code-reviewer` or `qa-tester` for final pressure test

## Cleanup Rules

### Keep
- `CLAUDE.md` as the full narrative brain
- `.ai/manifest.json` as machine-canonical index
- Codex skills for runtime/schema/widget constraints
- specialized agents that map cleanly to real work

### Thin down
- `AGENTS.md`

### Label as experimental
- GAN agents
- build-loop
- generated skills that are not part of the default path

### Avoid
- multiple files each claiming to be the primary orchestration source
- stale agent counts or old delegation orders in the manifest
- undocumented model-role drift

## Maintenance Rules
1. If agent inventory changes, update `.ai/manifest.json`
2. If orchestration defaults change, update both `CLAUDE.md` and `.ai/manifest.json`
3. If model role policy changes, update all three:
   - `CLAUDE.md`
   - `.ai/manifest.json`
   - `AGENTS.md`
4. Keep `AGENTS.md` short enough that drift is obvious and easy to fix

## Recommended Near-Term Follow-Ups
1. label experimental agents/skills directly in docs
2. centralize orchestration language around `coordinator`
3. remove stale references to the old 6-agent model from machine-readable docs
4. consider generating `.ai/manifest.json` from the actual filesystem to reduce drift
