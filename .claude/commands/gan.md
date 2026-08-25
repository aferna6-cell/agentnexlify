---
description: GAN harness — planner sets an ambitious spec, generator builds, a ruthless evaluator drives the live app and scores it against a weighted rubric until it passes.
argument-hint: [what to build]
model: opus
---

Drive the GAN loop for: `$ARGUMENTS`

Read `.claude/agents/gan-planner.md`, `gan-generator.md`, and `gan-evaluator.md` before starting — they own their own contracts and this file only sequences them.

**ultrathink** — the planner's ambition and the evaluator's strictness are where the quality comes from. Neither is a formality.

## Why this exists

Self-evaluation is a trap: a model grading its own work declares half-built features done. The evaluator runs in a **separate context** with a **harsh** prompt and drives the **running app** via Playwright — it does not read the generator's source and take its word for it. That separation is the entire point. Do not collapse it by letting the generator score itself.

## Step 0 — scaffold

```bash
python -m scripts.gan.init_harness --goal "$ARGUMENTS"
```

Creates `gan-harness/` (gitignored per-run state). Re-running is safe; it skips files that already exist. `--status` reports the iteration count.

## Step 1 — plan

Dispatch `gan-planner`. It writes `gan-harness/spec.md` and `gan-harness/eval-rubric.md`.

Hold it to its own brief: 12-16 features, deliberately ambitious, grouped into sprints. A conservative spec produces a forgettable result — that failure mode is the reason the agent's prompt says "be deliberately ambitious."

The rubric it writes must contain criteria checkable **by driving the app**, not by reading code. Reject "uses semantic HTML"; keep "keyboard-only user can complete the primary flow."

## Step 2 — build ↔ evaluate

Loop until PASS or the iteration cap:

1. Dispatch `gan-generator`. On iterations after the first it MUST read the newest `gan-harness/feedback/feedback-NNN.md` first and address **every** item — the evaluator's findings are not suggestions.
2. Dispatch `gan-evaluator`. It drives the live app, scores each axis 1-10, computes `(design*0.3) + (originality*0.2) + (craft*0.3) + (functionality*0.2)`, and writes the next `feedback-NNN.md`.
3. **PASS at >= 7.0 weighted.** Otherwise iterate.

Default cap: **5 iterations.** If it has not passed by then, stop and report the standing rubric gaps rather than grinding — a loop that will not converge is information, not a failure to hide.

## Step 3 — report

Give the user: final weighted score, per-axis breakdown, iteration count, and what the evaluator still flags. If it never reached 7.0, say so plainly and name the axis that blocked it.

## Rules

- **The generator never scores itself.** If it reports a score, discard it and dispatch the evaluator.
- **Evaluate at end-of-generation, not per-sprint.** Anthropic dropped per-sprint evaluation moving Opus 4.5 → 4.6 — same runtime, roughly half the cost. Per-sprint evaluation is scaffolding for a weaker model.
- **A regression is a finding.** The feedback template has a "What Regressed" section; a generator that fixes three things and breaks one has not made progress.
- **Do not soften the evaluator to close the loop.** If it is failing the build for real reasons, the build is wrong. Changing the rubric to pass is the same mistake as changing a test to pass (`user-rules.md` Rule 10).

## When NOT to use this

This is a greenfield UI-quality harness, and it is expensive — three Opus agents plus browser automation across up to 5 rounds. For brownfield work in this repo use `/compound` (5-agent pipeline) or `/orchestrate` (DAG waves). `docs/AGENT_SYSTEM_PLAN.md` names `coordinator` the canonical default orchestrator; this loop is the specialist tool, not the default.
