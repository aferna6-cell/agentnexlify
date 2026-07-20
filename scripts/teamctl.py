#!/usr/bin/env python3
"""Local CLI for the cross-provider Agent Nexlify team protocol."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / ".ai" / "team-contract.json"
EVENT_PREFIX = "<!-- agent-team:event "
EVENT_SUFFIX = " -->"
LANE_PATTERN = re.compile(r"[^a-z0-9]+")


class TeamError(RuntimeError):
    """A user-actionable team protocol error."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TeamError(f"Missing team contract: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TeamError(f"Invalid JSON in {path}: {exc}") from exc
    validate_contract(contract)
    return contract


def validate_contract(contract: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "north_star",
        "agents",
        "required_reads",
        "coordination",
        "review",
        "autonomy",
        "verification",
        "github_actions",
    }
    missing = sorted(required - contract.keys())
    if missing:
        raise TeamError(f"Team contract is missing: {', '.join(missing)}")

    expected_agents = {"codex", "fable5", "kimi3"}
    actual_agents = set(contract["agents"])
    if not expected_agents.issubset(actual_agents):
        missing_agents = sorted(expected_agents - actual_agents)
        raise TeamError(f"Team contract is missing agents: {', '.join(missing_agents)}")

    actions = contract["github_actions"]
    if actions.get("allowed_for_team_work") is not False:
        raise TeamError("GitHub Actions must be disabled for team work")
    if actions.get("required_commit_marker") != "[skip ci]":
        raise TeamError("Team commits must use the [skip ci] marker")

    if contract["review"].get("normal_peer_approvals", 0) < 1:
        raise TeamError("At least one peer approval is required")


def require_agent(contract: dict[str, Any], agent: str) -> None:
    if agent not in contract["agents"]:
        choices = ", ".join(sorted(contract["agents"]))
        raise TeamError(f"Unknown agent '{agent}'. Expected one of: {choices}")


def slug(value: str) -> str:
    result = LANE_PATTERN.sub("-", value.strip().lower()).strip("-")
    if not result:
        raise TeamError("Lane must contain at least one letter or number")
    return result[:60]


def branch_name(issue: int, agent: str, lane: str) -> str:
    return f"team/{issue}/{slug(agent)}/{slug(lane)}"


def make_event(
    event: str,
    issue: int,
    agent: str,
    lane: str,
    summary: str,
    *,
    now: datetime | None = None,
    **fields: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "event": event,
        "issue": issue,
        "agent": agent,
        "lane": slug(lane),
        "summary": summary.strip(),
        "timestamp": isoformat(now or utc_now()),
    }
    payload.update({key: value for key, value in fields.items() if value not in (None, "")})
    return payload


def event_marker(event: dict[str, Any]) -> str:
    payload = json.dumps(event, sort_keys=True, separators=(",", ":"))
    return f"{EVENT_PREFIX}{payload}{EVENT_SUFFIX}"


def render_comment(event: dict[str, Any]) -> str:
    heading = event["event"].replace("_", " ").title()
    lines = [
        f"### Agent team · {heading}",
        "",
        f"- **Agent:** `{event['agent']}`",
        f"- **Lane:** `{event['lane']}`",
        f"- **Summary:** {event['summary']}",
    ]
    labels = {
        "scope": "Scope",
        "to": "Handoff to",
        "expires_at": "Lease expires",
        "verdict": "Verdict",
        "command": "Local command",
        "result": "Result",
        "evidence": "Evidence",
        "dependencies": "Dependencies",
        "risk": "Risk",
    }
    for key, label in labels.items():
        if key in event:
            value = event[key]
            if key in {"command", "result", "verdict", "to", "risk"}:
                value = f"`{value}`"
            lines.append(f"- **{label}:** {value}")
    lines.extend(["", event_marker(event)])
    return "\n".join(lines)


def extract_events(comments: Iterable[dict[str, Any] | str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for comment in comments:
        body = comment if isinstance(comment, str) else str(comment.get("body", ""))
        for line in body.splitlines():
            line = line.strip()
            if not (line.startswith(EVENT_PREFIX) and line.endswith(EVENT_SUFFIX)):
                continue
            raw = line[len(EVENT_PREFIX) : -len(EVENT_SUFFIX)]
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and parsed.get("schema_version") == 1:
                events.append(parsed)
    return events


def sorted_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(event: dict[str, Any]) -> datetime:
        try:
            return parse_time(str(event["timestamp"]))
        except (KeyError, TypeError, ValueError):
            return datetime.min.replace(tzinfo=timezone.utc)

    return sorted(events, key=key)


def active_claims(
    events: Iterable[dict[str, Any]], now: datetime | None = None
) -> dict[str, dict[str, Any]]:
    current_time = now or utc_now()
    claims: dict[str, dict[str, Any]] = {}
    for event in sorted_events(events):
        lane = event.get("lane")
        if not lane:
            continue
        if event.get("event") == "claim":
            claims[lane] = event
        elif event.get("event") in {"handoff", "release", "complete"}:
            claims.pop(lane, None)

    return {
        lane: claim
        for lane, claim in claims.items()
        if not claim.get("expires_at") or parse_time(str(claim["expires_at"])) > current_time
    }


def readiness(
    events: Iterable[dict[str, Any]],
    lane: str,
    risk: str,
    contract: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    lane = slug(lane)
    relevant = [event for event in sorted_events(events) if event.get("lane") == lane]
    live_claim = active_claims(relevant, now).get(lane)
    claim_owner = live_claim.get("agent") if live_claim else None
    latest_change_index = max(
        (
            index
            for index, event in enumerate(relevant)
            if event.get("event") in {"claim", "update"}
        ),
        default=-1,
    )
    latest_reviews: dict[str, str] = {}
    passing_proof = False
    allowed_agents = set(contract["agents"])
    for event in relevant[latest_change_index + 1 :]:
        if (
            event.get("event") == "review"
            and event.get("agent") in allowed_agents
            and event.get("agent") != claim_owner
        ):
            latest_reviews[str(event.get("agent"))] = str(event.get("verdict"))
        if event.get("event") == "proof":
            passing_proof = str(event.get("result", "")).upper() == "PASS"

    approvals = sorted(agent for agent, verdict in latest_reviews.items() if verdict == "approve")
    required = contract["review"][
        "risky_peer_approvals" if risk == "risky" else "normal_peer_approvals"
    ]
    return {
        "lane": lane,
        "risk": risk,
        "claim_owner": claim_owner,
        "approvals": approvals,
        "required_approvals": required,
        "passing_proof": passing_proof,
        "ready": claim_owner in allowed_agents and len(approvals) >= required and passing_proof,
    }


def run_gh(arguments: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["gh", *arguments],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise TeamError("GitHub CLI (gh) is required for live team coordination") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown gh error"
        raise TeamError(detail)
    return completed.stdout.strip()


def fetch_issue(issue: int) -> dict[str, Any]:
    raw = run_gh(
        [
            "issue",
            "view",
            str(issue),
            "--json",
            "number,title,state,url,comments",
        ]
    )
    data = json.loads(raw)
    if data.get("state") != "OPEN":
        raise TeamError(f"Issue #{issue} is not open")
    return data


def post_event(issue: int, event: dict[str, Any]) -> None:
    run_gh(["issue", "comment", str(issue), "--body", render_comment(event)])
    print(f"Posted {event['event']} for `{event['lane']}` to issue #{issue}.")


def issue_events(
    issue: dict[str, Any], contract: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    comments = issue.get("comments", [])
    if contract is not None:
        trusted = set(contract["coordination"].get("trusted_github_actors", []))
        if trusted:
            comments = [
                comment
                for comment in comments
                if isinstance(comment, dict)
                and comment.get("author", {}).get("login") in trusted
            ]
    events = [
        event
        for event in extract_events(comments)
        if event.get("issue") == issue.get("number")
    ]
    if contract is not None:
        allowed_agents = set(contract["agents"])
        events = [event for event in events if event.get("agent") in allowed_agents]
    return events


def cmd_preflight(args: argparse.Namespace, contract: dict[str, Any]) -> None:
    require_agent(contract, args.agent)
    issue = fetch_issue(args.issue)
    claims = active_claims(issue_events(issue, contract))
    print(f"Issue #{issue['number']}: {issue['title']}")
    print(issue["url"])
    print(f"\nNorth star:\n{contract['north_star']}")
    print("\nRequired reads:")
    reads = list(contract["required_reads"])
    adapter = contract.get("provider_adapters", {}).get(args.agent)
    if adapter and adapter not in reads:
        reads.insert(3, adapter)
    for item in reads:
        state = "ok" if (ROOT / item).exists() else "MISSING"
        print(f"  [{state}] {item}")
    print("\nActive lane claims:")
    if not claims:
        print("  none")
    for lane, claim in sorted(claims.items()):
        print(f"  {lane}: {claim.get('agent')} until {claim.get('expires_at', 'released')}")
    print("\nNext: claim one unowned lane before editing.")


def cmd_status(args: argparse.Namespace, contract: dict[str, Any]) -> None:
    issue = fetch_issue(args.issue)
    events = issue_events(issue, contract)
    status = {
        "issue": {key: issue[key] for key in ("number", "title", "state", "url")},
        "north_star": contract["north_star"],
        "active_claims": active_claims(events),
        "event_count": len(events),
    }
    if args.json:
        print(json.dumps(status, indent=2, sort_keys=True))
        return
    print(f"Issue #{issue['number']}: {issue['title']} ({issue['state'].lower()})")
    print(f"Team events: {len(events)}")
    claims = status["active_claims"]
    if not claims:
        print("Active claims: none")
    else:
        print("Active claims:")
        for lane, claim in sorted(claims.items()):
            print(f"  {lane}: {claim.get('agent')} — {claim.get('scope', claim.get('summary'))}")


def cmd_claim(args: argparse.Namespace, contract: dict[str, Any]) -> None:
    require_agent(contract, args.agent)
    issue = fetch_issue(args.issue)
    lane = slug(args.lane)
    claims = active_claims(issue_events(issue, contract))
    existing = claims.get(lane)
    if existing and existing.get("agent") != args.agent:
        raise TeamError(
            f"Lane '{lane}' is already claimed by {existing.get('agent')} until "
            f"{existing.get('expires_at')}. Choose another lane or coordinate a handoff."
        )
    hours = args.lease_hours or contract["coordination"]["default_claim_lease_hours"]
    now = utc_now()
    event = make_event(
        "claim",
        args.issue,
        args.agent,
        lane,
        f"Claimed {lane}",
        now=now,
        scope=args.scope,
        dependencies=args.dependencies,
        expires_at=isoformat(now + timedelta(hours=hours)),
        branch=branch_name(args.issue, args.agent, lane),
    )
    post_event(args.issue, event)
    print(f"Branch/worktree: {event['branch']}")
    print("Install hooks there with: bash scripts/install-hooks.sh")


def cmd_simple_event(args: argparse.Namespace, contract: dict[str, Any]) -> None:
    require_agent(contract, args.agent)
    issue = fetch_issue(args.issue)
    events = issue_events(issue, contract)
    if args.command_name == "handoff":
        require_agent(contract, args.to)
        if args.to == args.agent:
            raise TeamError("A handoff recipient must be another agent")
    if args.command_name == "review":
        lane_claim = active_claims(events).get(slug(args.lane))
        if lane_claim and lane_claim.get("agent") == args.agent:
            raise TeamError("An agent cannot review its own active lane")
    fields: dict[str, Any] = {}
    for key in ("to", "verdict", "command", "result", "evidence", "risk"):
        if hasattr(args, key):
            fields[key] = getattr(args, key)
    event = make_event(
        args.command_name,
        args.issue,
        args.agent,
        args.lane,
        args.summary,
        **fields,
    )
    post_event(args.issue, event)


def cmd_ready(args: argparse.Namespace, contract: dict[str, Any]) -> None:
    issue = fetch_issue(args.issue)
    state = readiness(issue_events(issue, contract), args.lane, args.risk, contract)
    print(json.dumps(state, indent=2, sort_keys=True))
    if not state["ready"]:
        raise TeamError(
            f"Lane '{state['lane']}' is not ready: "
            f"{len(state['approvals'])}/{state['required_approvals']} approvals, "
            f"passing_proof={state['passing_proof']}"
        )


def common_event_parser(subparsers: Any, name: str, help_text: str) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(name, help=help_text)
    parser.set_defaults(handler=cmd_simple_event, command_name=name)
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--summary", required=True)
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Coordinate Codex, Fable 5, and Kimi 3 through one GitHub issue."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight", help="Load the contract and shared issue state")
    preflight.set_defaults(handler=cmd_preflight)
    preflight.add_argument("--issue", type=int, required=True)
    preflight.add_argument("--agent", required=True)

    status = subparsers.add_parser("status", help="Show live issue coordination state")
    status.set_defaults(handler=cmd_status)
    status.add_argument("--issue", type=int, required=True)
    status.add_argument("--json", action="store_true")

    claim = subparsers.add_parser("claim", help="Claim one exclusive implementation lane")
    claim.set_defaults(handler=cmd_claim)
    claim.add_argument("--issue", type=int, required=True)
    claim.add_argument("--agent", required=True)
    claim.add_argument("--lane", required=True)
    claim.add_argument("--scope", required=True)
    claim.add_argument("--dependencies", default="none")
    claim.add_argument("--lease-hours", type=int)

    common_event_parser(subparsers, "update", "Publish progress, a decision, risk, or blocker")

    handoff = common_event_parser(subparsers, "handoff", "Release a lane to a named teammate")
    handoff.add_argument("--to", required=True)
    handoff.add_argument("--evidence", default="")

    review = common_event_parser(subparsers, "review", "Record peer review of a lane")
    review.add_argument("--verdict", choices=("approve", "request_changes", "comment"), required=True)
    review.add_argument("--evidence", default="")

    proof = common_event_parser(subparsers, "proof", "Record local verification evidence")
    proof.add_argument("--command", required=True)
    proof.add_argument("--result", choices=("PASS", "FAIL", "WARN"), required=True)
    proof.add_argument("--evidence", required=True)

    release = common_event_parser(subparsers, "release", "Relinquish a lane without a handoff")

    ready = subparsers.add_parser("ready", help="Enforce proof and peer-approval requirements")
    ready.set_defaults(handler=cmd_ready)
    ready.add_argument("--issue", type=int, required=True)
    ready.add_argument("--lane", required=True)
    ready.add_argument("--risk", choices=("normal", "risky"), default="normal")

    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        contract = load_contract()
        args.handler(args, contract)
    except TeamError as exc:
        print(f"teamctl: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
