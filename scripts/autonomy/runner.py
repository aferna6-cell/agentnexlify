"""The subprocess seam every gate runs through.

Split out of ``gates.py`` for one reason: the gates are only testable if the
process boundary is injectable. Keeping the boundary in its own module makes
that seam an explicit part of the design instead of a private helper, and keeps
each file small enough to read in one sitting.

The contract is narrow on purpose — a runner takes an argv list plus ``cwd``
and ``timeout``, and returns a :class:`CommandResult`. A fake is four lines.
"""

import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# Enough tail to include ci_local.sh's whole summary block (its PASS/SKIP/FAIL
# roster plus the RESULT line), so a caller can name the failing gate without
# carrying the full multi-megabyte log around.
SUMMARY_LINES = 40

# `timeout(1)`'s convention. A distinct code keeps "the gate failed" and "the
# gate never finished" apart in logs and in the loop's branching.
TIMEOUT_RETURNCODE = 124
SPAWN_FAILED_RETURNCODE = -1


@dataclass
class CommandResult:
    """What a runner hands back. Deliberately smaller than ``CompletedProcess``.

    ``stdout`` carries merged stdout+stderr: gate failures are as likely to be
    on one stream as the other, and a summary missing half the output is worse
    than no summary.
    """

    returncode: int
    stdout: str = ""


Runner = Callable[..., CommandResult]


@dataclass
class GateResult:
    """The outcome of one verification gate. ``passed=False`` is a normal value."""

    passed: bool
    name: str
    summary: str
    duration_seconds: float
    returncode: int


def subprocess_runner(
    command: list[str],
    *,
    cwd: str | Path | None = None,
    timeout: float | None = None,
) -> CommandResult:
    """Run ``command`` for real. The production default for every gate."""
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
        command,
        cwd=str(cwd) if cwd is not None else None,
        timeout=timeout,
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=(completed.stdout or "") + (completed.stderr or ""),
    )


def tail(text: str) -> str:
    """Last :data:`SUMMARY_LINES` meaningful lines, or a marker when there are none."""
    lines = (text or "").strip().splitlines()
    if not lines:
        return "(no output)"
    return "\n".join(lines[-SUMMARY_LINES:])


def run_gate(
    name: str,
    command: list[str],
    *,
    runner: Runner | None,
    timeout: float | None,
    cwd: str | Path | None = None,
) -> GateResult:
    """Execute one gate and translate every failure mode into a ``GateResult``.

    Timeout returns ``passed=False`` rather than raising. Raising here would
    make the single most likely failure of a long CI run — a hung gate — the
    one failure the loop cannot handle uniformly, and the loop would die
    holding an uncommitted tree. The distinct :data:`TIMEOUT_RETURNCODE` plus
    the summary text keep it distinguishable from an ordinary red gate.

    A runner that cannot even start (no ``bash``, no ``npm``) is the same kind
    of answer: unverified, reported, not raised.
    """
    run = runner or subprocess_runner
    started = time.monotonic()
    try:
        result = run(command, cwd=cwd, timeout=timeout)
    except subprocess.TimeoutExpired:
        return GateResult(
            passed=False,
            name=name,
            summary=(
                f"TIMEOUT: {' '.join(command)} exceeded {timeout}s and was killed. "
                f"No gate verdict was produced; treat this as unverified, not green."
            ),
            duration_seconds=round(time.monotonic() - started, 3),
            returncode=TIMEOUT_RETURNCODE,
        )
    except OSError as exc:
        return GateResult(
            passed=False,
            name=name,
            summary=f"COULD NOT START: {' '.join(command)} — {exc}",
            duration_seconds=round(time.monotonic() - started, 3),
            returncode=SPAWN_FAILED_RETURNCODE,
        )
    return GateResult(
        passed=result.returncode == 0,
        name=name,
        summary=tail(result.stdout),
        duration_seconds=round(time.monotonic() - started, 3),
        returncode=result.returncode,
    )
