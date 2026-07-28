"""Deterministic safety gates — the checks the loop runs before it is allowed to act.

`planning/decisions/2026-07-27-autonomous-engineering-substrate.md` lists the
guardrails that must exist before any autonomous loop is armed: local CI as the
only verification currency, no work on the default branch, and a hard cap on
PRs per day. Each one is a fact about the working copy or a count, so each one
is answered here by a subprocess or arithmetic rather than by a model. A gate
that needs an LLM to decide "did CI pass" is a gate that can be talked out of
its answer.

Two rules shape every signature below:

**A failed gate is data, not an exception.** The loop decides what a red gate
means — retry, escalate, or idle. Raising would collapse that choice into a
crash, and a loop that crashes leaves a half-finished branch behind.

**Every subprocess goes through an injectable ``runner``** from
:mod:`scripts.autonomy.runner`. Tests pass a fake; production gets
:func:`~scripts.autonomy.runner.subprocess_runner`. Without the seam these
gates could only be exercised by actually running a 20-gate CI suite, so in
practice they would not be exercised at all.
"""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from scripts.autonomy.runner import (
    SPAWN_FAILED_RETURNCODE,
    CommandResult,
    GateResult,
    Runner,
    run_gate,
    subprocess_runner,
)

__all__ = [
    "DEFAULT_BRANCH",
    "DEFAULT_DEPLOY_PRESSURE_CEILING",
    "DEFAULT_MAX_PRS_PER_DAY",
    "GateResult",
    "GitState",
    "PreflightReport",
    "deploy_budget_remaining",
    "deploy_pressure_exceeded",
    "git_state",
    "migration_number_conflict",
    "preflight",
    "run_local_ci",
    "run_quick_check",
]

# 2026-06-23: eleven merged PRs exhausted Vercel's free-tier 100-deploys/day
# cap and blocked every frontend deploy for ~24h. Each PR is worth far more
# than one deploy — preview builds fire on TWO Vercel projects ("agentnexlify"
# for landing-page-v2 and "app.agentnexlify" for frontend/), and each
# draft→ready transition and follow-up push rebuilds both. Budgeting 4 PRs/day
# keeps a normal day's churn well inside the cap with room for retries.
DEFAULT_MAX_PRS_PER_DAY = 4

# Total PR volume (any author) at which the loop stands down entirely. Separate
# from its own allowance above; see deploy_pressure_exceeded for why it is high.
DEFAULT_DEPLOY_PRESSURE_CEILING = 60

DEFAULT_BRANCH = "main"

# Tolerant on the separator: migrations/ is overwhelmingly `NNN_name.sql` but
# `081-kb-articles-and-sources.sql` exists, and a number we fail to see is a
# number we would hand out twice.
_MIGRATION_NUMBER = re.compile(r"^(\d+)[_-]")


@dataclass
class GitState:
    """A snapshot of the working copy the loop is about to write into."""

    branch: str
    is_clean: bool
    head_sha: str
    untracked_count: int
    ahead: int
    behind: int


@dataclass
class PreflightReport:
    """Whether the loop may start, and if not, what a human should do about it."""

    ok: bool
    blockers: list[str] = field(default_factory=list)


def run_local_ci(
    compare_ref: str = "origin/main",
    *,
    runner: Runner | None = None,
    timeout: int = 3600,
) -> GateResult:
    """Run the 20-gate local CI mirror (`scripts/ci_local.sh`).

    This is the loop's only accepted evidence that a change is safe to open a
    PR for: GH #500 left hosted Actions failing on a spending limit, so a green
    hosted run cannot be relied on. The script's trailing summary block names
    every failing gate, which is why the summary keeps the tail rather than the
    head of the output.
    """
    return run_gate(
        "local-ci",
        ["bash", "scripts/ci_local.sh", compare_ref],
        runner=runner,
        timeout=timeout,
    )


def run_quick_check(*, runner: Runner | None = None, timeout: int = 900) -> GateResult:
    """Run `npm run check:quick` — the cheap lane the loop can afford to repeat.

    :func:`run_local_ci` costs minutes and is the gate for landing work. This
    one costs seconds and is the gate for iterating: a loop that runs full CI
    after every edit spends its whole budget on verification.
    """
    return run_gate(
        "quick-check",
        ["npm", "run", "check:quick", "--silent"],
        runner=runner,
        timeout=timeout,
    )


def _git(runner: Runner, args: list[str], cwd: str | Path | None) -> CommandResult:
    """Run one git command, converting a missing or hung git into a soft result."""
    try:
        return runner(["git", *args], cwd=cwd, timeout=30)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return CommandResult(returncode=SPAWN_FAILED_RETURNCODE, stdout=str(exc))


def git_state(
    *,
    runner: Runner | None = None,
    cwd: str | Path | None = None,
) -> GitState:
    """Read the working copy's branch, cleanliness, HEAD, and upstream delta.

    Every field feeds a decision the loop must not get wrong: which branch it
    is about to commit to, whether it is about to sweep up someone else's
    uncommitted work, and how far it has drifted from its upstream. A branch
    with no upstream is normal for a freshly created loop branch, so
    ``ahead``/``behind`` degrade to ``0/0`` instead of failing.
    """
    run = runner or subprocess_runner

    branch_result = _git(run, ["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""

    status_result = _git(run, ["status", "--porcelain"], cwd)
    status_lines = [ln for ln in status_result.stdout.splitlines() if ln.strip()]
    # A failed `git status` must not read as "clean" — that is the one wrong
    # answer that lets the loop commit over someone else's work.
    is_clean = status_result.returncode == 0 and not status_lines
    untracked_count = sum(1 for ln in status_lines if ln.startswith("??"))

    sha_result = _git(run, ["rev-parse", "HEAD"], cwd)
    head_sha = sha_result.stdout.strip() if sha_result.returncode == 0 else ""

    ahead = behind = 0
    upstream = _git(run, ["rev-list", "--left-right", "--count", "@{u}...HEAD"], cwd)
    if upstream.returncode == 0:
        parts = upstream.stdout.split()
        if len(parts) == 2 and all(p.isdigit() for p in parts):
            # Left side is @{u} — commits upstream has that HEAD does not.
            behind, ahead = int(parts[0]), int(parts[1])

    return GitState(
        branch=branch,
        is_clean=is_clean,
        head_sha=head_sha,
        untracked_count=untracked_count,
        ahead=ahead,
        behind=behind,
    )


def deploy_budget_remaining(
    loop_prs_opened_today: int,
    *,
    max_prs_per_day: int = DEFAULT_MAX_PRS_PER_DAY,
) -> int:
    """How many more PRs THE LOOP may open today. Its own allowance, nothing else.

    On 2026-06-23 the loop merged eleven PRs in one session and blew Vercel's
    free-tier limit of 100 deploys/day, blocking every frontend deploy for
    roughly 24 hours. A PR is not one deploy: preview builds fire on two Vercel
    projects, and each draft→ready transition and follow-up push rebuilds both,
    so the real multiplier is several deploys per PR. The default of 4 keeps a
    full day of loop output well under the cap with headroom for the retries
    that follow a red gate.

    This counts only PRs the loop itself opened. Counting *every* PR was the
    original mistake and it showed up the first time this ran for real: 20 PRs
    had been opened that day, 18 of them Dependabot, so the loop stood down over
    churn it neither caused nor could influence. Dependabot batches are routine
    here, which would have made "blocked" the normal state. Total volume is a
    real concern, but it is a different one — see
    :func:`deploy_pressure_exceeded`.

    Never returns a negative number — "how many may I open" has no meaningful
    answer below zero, and a negative would silently pass a ``> 0`` check
    inverted somewhere downstream.
    """
    return max(0, max_prs_per_day - max(0, loop_prs_opened_today))


def deploy_pressure_exceeded(
    total_prs_opened_today: int,
    *,
    ceiling: int = DEFAULT_DEPLOY_PRESSURE_CEILING,
) -> bool:
    """Whether total PR volume today is close enough to the cap to stand down.

    The emergency brake, separate from the loop's own allowance. It exists for
    the case where something else — a large Dependabot batch, a human sprint —
    has already consumed most of the day's deploys, and the marginal PR really
    would be the one that tips it.

    The ceiling is high on purpose. At roughly 2-3 deploys per PR against a
    100/day cap, ~60 PRs is where the next one plausibly matters; anything much
    lower re-creates the bug this split was made to fix, where ordinary bot
    churn silences the loop. ``0`` means "unknown", not "quiet", so an unset
    count never trips the brake.
    """
    return total_prs_opened_today >= ceiling


def migration_number_conflict(
    repo_root: str | Path,
    claimed: int,
    *,
    extra_claimed: list[int] | None = None,
) -> int | None:
    """Return the next free migration number if ``claimed`` is taken, else ``None``.

    Migration numbers are allocated by looking at `migrations/`, which only
    shows *merged* work. On this branch that produced a real collision: 188 was
    claimed by both PR #575 and PR #599 because neither could see the other's
    unmerged file. ``extra_claimed`` is where the loop passes the numbers held
    by open PRs so the second caller picks 189 instead of a duplicate.

    The suggestion starts above the highest number on disk rather than at the
    first hole. Reusing a gap looks tidy and is a trap — a gap usually means a
    migration is in flight, and sequential numbering is what makes the
    ci_local.sh numbering gate meaningful.
    """
    directory = Path(repo_root) / "migrations"
    existing: set[int] = set()
    if directory.is_dir():
        for path in directory.glob("*.sql"):
            match = _MIGRATION_NUMBER.match(path.name)
            if match:
                existing.add(int(match.group(1)))

    taken = existing | set(extra_claimed or [])
    if claimed not in taken:
        return None

    candidate = (max(existing) if existing else 0) + 1
    while candidate in taken:
        candidate += 1
    return candidate


def preflight(
    *,
    runner: Runner | None = None,
    repo_root: str | Path | None = None,
    loop_prs_opened_today: int = 0,
    total_prs_opened_today: int = 0,
) -> PreflightReport:
    """Decide whether the loop may start at all, before it spends a single token.

    Three conditions, each one a real way an autonomous run goes wrong:
    committing to the default branch, sweeping a human's uncommitted work into
    its own commit, and opening PRs past the deploy budget. Blockers are
    sentences a human can act on, because the loop's escalation path is a
    message to a person.
    """
    state = git_state(runner=runner, cwd=repo_root)
    blockers: list[str] = []

    if state.branch == DEFAULT_BRANCH:
        blockers.append(
            f"Working copy is on {DEFAULT_BRANCH!r}. The loop never commits to the "
            f"default branch — create and check out a working branch first."
        )
    elif state.branch in ("", "HEAD"):
        blockers.append(
            "Git HEAD is detached or unreadable, so there is no branch to push. "
            "Check out a named working branch first."
        )

    if not state.is_clean:
        blockers.append(
            f"Working tree is dirty ({state.untracked_count} untracked file(s) "
            f"among the changes). Commit or stash before the loop starts, so its "
            f"commits contain only its own work."
        )

    if deploy_budget_remaining(loop_prs_opened_today) <= 0:
        blockers.append(
            f"The loop's own daily PR allowance is spent: it opened "
            f"{loop_prs_opened_today} today ({DEFAULT_MAX_PRS_PER_DAY} allowed). "
            f"Wait for the daily reset — the 2026-06-23 incident blocked all "
            f"frontend deploys for 24h."
        )

    if deploy_pressure_exceeded(total_prs_opened_today):
        blockers.append(
            f"Total PR volume today is {total_prs_opened_today} "
            f"(ceiling {DEFAULT_DEPLOY_PRESSURE_CEILING}); the day's Vercel deploy "
            f"budget is close to spent regardless of who used it. Stand down until "
            f"it resets."
        )

    return PreflightReport(ok=not blockers, blockers=blockers)
