"""Scaffold the `gan-harness/` working directory for the GAN agent loop.

The three GAN agents (`.claude/agents/gan-planner.md`, `gan-generator.md`,
`gan-evaluator.md`) coordinate entirely through files on disk:

    gan-harness/
      spec.md                    written by planner, read by generator
      eval-rubric.md             written by planner, read by evaluator
      generator-state.md         generator's running notes across iterations
      feedback/feedback-001.md   evaluator -> generator, one per iteration
      feedback/feedback-002.md
      ...

Until 2026-08-24 nothing created this directory and no driver invoked the
agents, so the loop had never actually run. `/gan` is the driver; this script
is the scaffolding step it calls first.

Idempotent: existing files are left alone unless --force is passed.

Usage:
    python -m scripts.gan.init_harness --goal "retro game maker"
    python -m scripts.gan.init_harness --goal "..." --force
    python -m scripts.gan.init_harness --status
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS_DIR = _REPO_ROOT / "gan-harness"
FEEDBACK_DIR = HARNESS_DIR / "feedback"

# Mirrors the weights in .claude/agents/gan-evaluator.md. If you change them
# there, change them here — the evaluator reads eval-rubric.md, not this file.
_RUBRIC_TEMPLATE = """# Evaluation Rubric

Weighted score = (design * 0.3) + (originality * 0.2) + (craft * 0.3) + (functionality * 0.2)

PASS threshold: >= 7.0 weighted.

Each axis is scored 1-10 against the calibration ladder in
`.claude/agents/gan-evaluator.md` — anchored to what a good human developer
would ship, NOT to "good for an AI".

| Axis | Weight | What it measures |
|---|---|---|
| Design Quality | 0.3 | Visual hierarchy, spacing, typography, restraint |
| Originality | 0.2 | Does it avoid the generic AI look? |
| Craft | 0.3 | Polish, states, edge cases, responsiveness |
| Functionality | 0.2 | Does the thing actually work when driven? |

## Project-specific criteria

<!-- The planner appends negotiated, testable criteria here. Each one must be
     checkable by driving the running app, not by reading the source. -->
"""

_STATE_TEMPLATE = """# Generator State

Iteration: 0
Last evaluator score: n/a

## Decisions made

<!-- Generator appends: what was built, what was deliberately deferred. -->

## Known gaps

<!-- Generator appends: what it knows is incomplete, so the evaluator does not
     have to rediscover it. Honesty here is cheaper than a wasted round. -->
"""


def _write(path: Path, content: str, *, force: bool) -> bool:
    """Write `content` to `path`. Returns True if written, False if skipped."""
    if path.exists() and not force:
        return False
    path.write_text(content)
    return True


def scaffold(goal: str, *, force: bool) -> int:
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    spec = (
        f"# Spec\n\n"
        f"Goal: {goal}\n\n"
        f"Scaffolded {stamp} by scripts/gan/init_harness.py.\n\n"
        f"<!-- The gan-planner agent overwrites this file with the real spec:\n"
        f"     12-16 ambitious features, grouped into sprints. Do not hand-write\n"
        f"     it — run /gan and let the planner produce it. -->\n"
    )

    written = []
    for path, content in (
        (HARNESS_DIR / "spec.md", spec),
        (HARNESS_DIR / "eval-rubric.md", _RUBRIC_TEMPLATE),
        (HARNESS_DIR / "generator-state.md", _STATE_TEMPLATE),
    ):
        if _write(path, content, force=force):
            written.append(path.relative_to(_REPO_ROOT))
        else:
            print(f"  skip (exists): {path.relative_to(_REPO_ROOT)}")

    for path in written:
        print(f"  wrote: {path}")

    print(f"\nHarness ready at {HARNESS_DIR.relative_to(_REPO_ROOT)}/")
    print("Next: the /gan command drives planner -> generator <-> evaluator.")
    return 0


def status() -> int:
    if not HARNESS_DIR.exists():
        print("gan-harness/ does not exist. Run with --goal to scaffold it.")
        return 1
    feedback = sorted(FEEDBACK_DIR.glob("feedback-*.md")) if FEEDBACK_DIR.exists() else []
    print(f"harness:    {HARNESS_DIR.relative_to(_REPO_ROOT)}/")
    for name in ("spec.md", "eval-rubric.md", "generator-state.md"):
        mark = "present" if (HARNESS_DIR / name).exists() else "MISSING"
        print(f"  {name:<20} {mark}")
    print(f"iterations: {len(feedback)}")
    if feedback:
        print(f"  latest:   {feedback[-1].relative_to(_REPO_ROOT)}")
    return 0


def main() -> int:
    # `__doc__` is None under `python -OO`, which strips docstrings.
    parser = argparse.ArgumentParser(
        description=(__doc__ or "Scaffold the gan-harness/ directory.").split("\n")[0]
    )
    parser.add_argument("--goal", help="One-line description of what to build.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing harness files instead of skipping them.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Report harness state and iteration count, then exit.",
    )
    args = parser.parse_args()

    if args.status:
        return status()
    if not args.goal:
        parser.error("--goal is required unless --status is passed")
    return scaffold(args.goal, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
