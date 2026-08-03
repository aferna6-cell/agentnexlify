"""CLI driver for the autonomous engineering loop.

The loop runs across several separate process invocations, because the work in
the middle of it is done by the Claude Code session that calls this, not by
this process. The protocol is deliberately small:

    python3 -m scripts.autonomy.run_loop start --backlog backlog.json
    -> {"run_id": "...", "status": "awaiting_action", "action": "implement", ...}

    # session performs the action, then:
    python3 -m scripts.autonomy.run_loop resume --run-id ... --result '{"summary":"..."}'
    -> {"status": "awaiting_action", "action": "open_pr", ...}   # or a terminal status

Every response is one JSON object on stdout, so the caller never parses prose.
Diagnostics go to stderr. The exit code is 0 whenever the loop advanced
correctly — including when it decides to idle or escalate, which are successful
outcomes, not errors. A non-zero exit means the driver itself broke.

State lives in ``--state-dir`` (default ``.autonomy/``) via the graph package's
``FileCheckpointer``, which is what makes resuming in a *different process*
work at all.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from backend.graph import (
    STATUS_AWAITING_INPUT,
    FileCheckpointer,
    resume as graph_resume,
    run as graph_run,
)
from scripts.autonomy import gates
from scripts.autonomy.backlog import load_items
from scripts.autonomy.loop_graph import build, default_budget
from scripts.autonomy.sweeper import DEFAULT_STALE_AFTER_SECONDS, find_stranded, sweep

DEFAULT_STATE_DIR = ".autonomy"


def _response(result, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Flatten a RunResult into the one JSON shape the session consumes."""
    payload: dict[str, Any] = {
        "run_id": result.run_id,
        "status": "awaiting_action"
        if result.status == STATUS_AWAITING_INPUT
        else result.status,
        "journal": result.state.get("journal", []),
        "outcome": result.state.get("outcome"),
        "supersteps": result.superstep,
        "budget": result.budget,
    }
    if result.status == STATUS_AWAITING_INPUT:
        info = result.interrupt or {}
        interrupted = (info.get("nodes") or [None])[0]
        action_payload = (info.get("payloads") or {}).get(interrupted, {})
        payload["action"] = action_payload.get("action", interrupted)
        payload["payload"] = action_payload
    if result.error:
        payload["error"] = result.error
    if extra:
        payload.update(extra)
    return payload


def _emit(data: dict[str, Any]) -> None:
    json.dump(data, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def _checkpointer(state_dir: str) -> FileCheckpointer:
    return FileCheckpointer(Path(state_dir))


def _parse_result(raw: str) -> Any:
    """Accept inline JSON or ``@path`` so large payloads skip the shell."""
    if raw.startswith("@"):
        raw = Path(raw[1:]).read_text()
    return json.loads(raw)


async def _cmd_start(args) -> dict[str, Any]:
    if not args.skip_preflight:
        report = gates.preflight(
            loop_prs_opened_today=args.prs_opened_today,
            total_prs_opened_today=args.total_prs_today,
        )
        if not report.ok:
            # Refusing here rather than in the Routine prompt is deliberate: a
            # prompt is advice, and the whole point of the guardrail is that it
            # holds when the session is having a bad day.
            return {
                "status": "blocked",
                "blockers": report.blockers,
                "journal": [],
            }

    items = load_items(args.backlog)
    graph = build()
    result = await graph_run(
        graph,
        {
            "backlog": [
                {
                    "id": i.id,
                    "title": i.title,
                    "value": i.value,
                    "effort": i.effort,
                    "confidence": i.confidence,
                    "risk": i.risk,
                    "labels": list(i.labels),
                    "blocked": i.blocked,
                    "blocked_reason": i.blocked_reason,
                    "owner_gated": i.owner_gated,
                    "touches_frontend": i.touches_frontend,
                    "url": i.url,
                }
                for i in items
            ],
            "exclude_ids": args.exclude or [],
            "allow_frontend": not args.no_frontend,
            "idle_rounds": args.idle_rounds,
        },
        run_id=args.run_id,
        budget=default_budget(),
        checkpointer=_checkpointer(args.state_dir),
        extras={
            "compare_ref": args.compare_ref,
            "loop_prs_opened_today": args.prs_opened_today,
        },
    )
    return _response(result, extra={"candidates": len(items)})


async def _cmd_resume(args) -> dict[str, Any]:
    result = await graph_resume(
        build(),
        args.run_id,
        _parse_result(args.result),
        checkpointer=_checkpointer(args.state_dir),
        budget=default_budget(),
        extras={
            "compare_ref": args.compare_ref,
            "loop_prs_opened_today": args.prs_opened_today,
        },
    )
    return _response(result)


async def _cmd_status(args) -> dict[str, Any]:
    checkpoint = await _checkpointer(args.state_dir).load(args.run_id)
    if checkpoint is None:
        return {"run_id": args.run_id, "status": "unknown"}
    info = checkpoint.interrupt or {}
    interrupted = (info.get("nodes") or [None])[0]
    action_payload = (info.get("payloads") or {}).get(interrupted, {})
    return {
        "run_id": checkpoint.run_id,
        "status": "awaiting_action"
        if checkpoint.status == STATUS_AWAITING_INPUT
        else checkpoint.status,
        "action": action_payload.get("action", interrupted),
        "outcome": checkpoint.state.get("outcome"),
        "journal": checkpoint.state.get("journal", []),
        "superstep": checkpoint.superstep,
    }


async def _cmd_list(args) -> dict[str, Any]:
    """Every run in the state dir, with stranded ones flagged.

    Half of #605 was that a dead run could only be found by already knowing
    its id. This is the discovery surface: no ids required.
    """
    root = Path(args.state_dir)
    store = _checkpointer(args.state_dir)
    # to_thread because the sweeper is synchronous and drives the checkpointer
    # with its own asyncio.run — calling it directly from inside this event
    # loop would nest loops and crash.
    found = await asyncio.to_thread(
        find_stranded, root, stale_after_seconds=args.stale_after
    )
    stranded_ids = {r.run_id for r in found}
    runs = []
    if root.is_dir():
        for run_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            checkpoint = await store.load(run_dir.name)
            if checkpoint is None:
                continue
            runs.append(
                {
                    "run_id": checkpoint.run_id,
                    "status": checkpoint.status,
                    "outcome": checkpoint.state.get("outcome"),
                    "frontier": checkpoint.frontier,
                    "stranded": checkpoint.run_id in stranded_ids,
                }
            )
    return {"runs": runs, "stranded": sorted(stranded_ids)}


async def _cmd_sweep(args) -> dict[str, Any]:
    # Same nested-event-loop consideration as _cmd_list.
    swept = await asyncio.to_thread(
        sweep,
        Path(args.state_dir),
        stale_after_seconds=args.stale_after,
        dry_run=args.dry_run,
    )
    return {
        "swept" if not args.dry_run else "would_sweep": [
            {
                "run_id": r.run_id,
                "frontier": r.frontier,
                "age_seconds": int(r.age_seconds),
                "safe_to_retry": r.safe_to_retry,
            }
            for r in swept
        ],
        "dry_run": args.dry_run,
    }


# Real defaults live here, not on the arguments — see _common_options.
_DEFAULTS = {
    "state_dir": DEFAULT_STATE_DIR,
    "compare_ref": "origin/main",
    "prs_opened_today": 0,
    "total_prs_today": 0,
}


def _common_options() -> argparse.ArgumentParser:
    """Options accepted on both sides of the subcommand.

    argparse only matches a parent-level flag *before* the subcommand, and
    `run_loop start --state-dir X` is what anyone actually types — so these are
    attached to the parent and to every subparser.

    The defaults are ``SUPPRESS`` rather than real values, which is the part
    that is easy to get wrong: when the same option is defined in both places,
    the subparser applies its own default *after* the parent has already parsed
    the flag, silently overwriting it. `--state-dir X start` then writes to
    `.autonomy/` while reporting success. Suppressing means an unsupplied flag
    sets no attribute at all, and :func:`_apply_defaults` fills it in once.
    """
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--state-dir",
        default=argparse.SUPPRESS,
        help=f"checkpoint directory (default {DEFAULT_STATE_DIR})",
    )
    common.add_argument(
        "--compare-ref",
        default=argparse.SUPPRESS,
        help="ref the local CI gate diffs against (default origin/main)",
    )
    common.add_argument(
        "--total-prs-today",
        type=int,
        default=argparse.SUPPRESS,
        help=(
            "PRs opened today by ANY author, including bots. Only trips the "
            "high deploy-pressure ceiling; 0 means unknown, not quiet."
        ),
    )
    common.add_argument(
        "--prs-opened-today",
        type=int,
        default=argparse.SUPPRESS,
        help=(
            "PRs the LOOP opened today — its own daily allowance. Does not "
            "count PRs from anyone else; use --total-prs-today for those."
        ),
    )
    return common


def _apply_defaults(args: argparse.Namespace) -> argparse.Namespace:
    for name, value in _DEFAULTS.items():
        if not hasattr(args, name):
            setattr(args, name, value)
    return args


def build_parser() -> argparse.ArgumentParser:
    common = _common_options()
    parser = argparse.ArgumentParser(
        prog="run_loop",
        description="Drive one task through the autonomous engineering loop.",
        parents=[common],
    )
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser(
        "start", help="begin a run from a scored backlog", parents=[common]
    )
    start.add_argument("--backlog", required=True, help="path to backlog JSON")
    start.add_argument("--run-id", default=None)
    start.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="work item ids already attempted this cycle",
    )
    start.add_argument(
        "--no-frontend",
        action="store_true",
        help="skip frontend-touching work (use when the deploy quota is spent)",
    )
    start.add_argument(
        "--skip-preflight",
        action="store_true",
        help=(
            "skip the branch/clean-tree/quota precondition. Diagnostics and "
            "tests only — the Routine never passes this."
        ),
    )
    start.add_argument(
        "--idle-rounds",
        type=int,
        default=0,
        help="consecutive prior rounds that found nothing",
    )
    start.set_defaults(func=_cmd_start)

    res = sub.add_parser(
        "resume", help="continue a run awaiting an action", parents=[common]
    )
    res.add_argument("--run-id", required=True)
    res.add_argument(
        "--result",
        required=True,
        help='JSON result of the action, or @path to a file containing it',
    )
    res.set_defaults(func=_cmd_resume)

    status = sub.add_parser(
        "status", help="inspect a run without advancing it", parents=[common]
    )
    status.add_argument("--run-id", required=True)
    status.set_defaults(func=_cmd_status)

    listing = sub.add_parser(
        "list", help="show every run; flag stranded ones", parents=[common]
    )
    listing.add_argument(
        "--stale-after",
        type=float,
        default=DEFAULT_STALE_AFTER_SECONDS,
        help="seconds of silence before a 'running' run counts as stranded",
    )
    listing.set_defaults(func=_cmd_list)

    sweep_cmd = sub.add_parser(
        "sweep",
        help="resolve stranded 'running' runs to failed (never re-runs a node)",
        parents=[common],
    )
    sweep_cmd.add_argument(
        "--stale-after",
        type=float,
        default=DEFAULT_STALE_AFTER_SECONDS,
        help="seconds of silence before a 'running' run counts as stranded",
    )
    sweep_cmd.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be swept without writing anything",
    )
    sweep_cmd.set_defaults(func=_cmd_sweep)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _apply_defaults(build_parser().parse_args(argv))
    try:
        _emit(asyncio.run(args.func(args)))
    except Exception as exc:  # noqa: BLE001 - CLI boundary: report, never traceback
        print(f"run_loop failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        _emit({"status": "driver_error", "error": f"{type(exc).__name__}: {exc}"})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
