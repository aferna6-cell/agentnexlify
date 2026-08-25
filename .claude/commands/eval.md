---
description: Eval-driven development harness. Use for define, check, or report on a feature's evals.
argument-hint: [define|check|report] [feature-name]
model: sonnet
---

Run the eval-harness workflow. Read `.claude/skills/eval-harness/SKILL.md` first — it owns the eval formats, grader types, and metrics.

Arguments: `$ARGUMENTS` — first word is the subcommand, rest is the feature name.

## define

Write the eval definition to `.claude/evals/<feature-name>.md` BEFORE any implementation:
- Capability evals — what Claude should newly be able to do, with checkbox success criteria
- Regression evals — what must keep working, with a baseline SHA or checkpoint
- Success metrics — target pass@k for capability, pass^k for regression

Use the `[CAPABILITY EVAL: ...]` and `[REGRESSION EVAL: ...]` block formats from the skill.

## check

Read `.claude/evals/<feature-name>.md`, run every eval, report PASS/FAIL per item.

Prefer code-based graders (grep, test run, build) over model-based graders. Flag anything security-related for human review instead of auto-grading. Append the run to `.claude/evals/<feature-name>.log`.

## report

Generate the full eval report in the skill's report format: capability results, regression results, pass@1 / pass@3 metrics, and an overall status line.

## No subcommand given

Ask which of define / check / report is wanted, and for which feature.
