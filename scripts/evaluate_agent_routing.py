#!/usr/bin/env python3
"""Validate and export the AgentNexLiFy agent-routing eval catalog."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "agent-routing-eval.json"

REQUIRED_LABELS = {"ai-routine", "ai-docs", "ai-tests", "ai-risky"}
REQUIRED_ROUTES = {
    "premium-codex-claude",
    "low-cost-routine",
    "low-cost-docs",
    "low-cost-tests",
    "batch-candidate",
}
REQUIRED_TASK_FIELDS = {
    "id",
    "title",
    "prompt",
    "expected_route",
    "labels",
    "risk_level",
    "surfaces",
    "verification",
    "success_criteria",
    "disallowed_modes",
}
HIGH_RISK_TERMS = {
    "auth",
    "billing",
    "pricing",
    "stripe",
    "supabase rls",
    "migration",
    "secret",
    "legal",
    "customer communication",
    "production deploy",
    "runtime ai policy",
}


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _as_list(value: object) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _contains_high_risk_term(task: dict) -> bool:
    text = " ".join(
        [
            str(task.get("title") or ""),
            str(task.get("prompt") or ""),
            " ".join(_as_list(task.get("surfaces"))),
            " ".join(_as_list(task.get("labels"))),
        ]
    ).lower()
    return any(term in text for term in HIGH_RISK_TERMS)


def inferred_route(task: dict) -> str:
    labels = set(_as_list(task.get("labels")))
    risk = str(task.get("risk_level") or "").lower()
    if risk == "high" or "ai-risky" in labels or _contains_high_risk_term(task):
        return "premium-codex-claude"
    if "ai-tests" in labels:
        return "low-cost-tests"
    if "ai-docs" in labels:
        surfaces = " ".join(_as_list(task.get("surfaces"))).lower()
        if "output/" in surfaces or risk == "medium":
            return "batch-candidate"
        return "low-cost-docs"
    return "low-cost-routine"


def validate_config(data: dict) -> List[str]:
    failures: List[str] = []

    labels = set(_as_list(data.get("required_labels")))
    missing_labels = REQUIRED_LABELS - labels
    if missing_labels:
        failures.append(f"missing required labels: {sorted(missing_labels)}")

    routes = data.get("routes")
    if not isinstance(routes, dict):
        failures.append("routes must be an object")
        routes = {}

    missing_routes = REQUIRED_ROUTES - set(routes)
    if missing_routes:
        failures.append(f"missing required routes: {sorted(missing_routes)}")

    for route_id, route in routes.items():
        if not isinstance(route, dict):
            failures.append(f"route {route_id} must be an object")
            continue
        for field in ("model_target", "use_when", "forbidden_when"):
            if not str(route.get(field) or "").strip():
                failures.append(f"route {route_id} missing {field}")

    tasks = data.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        failures.append("tasks must be a non-empty list")
        tasks = []

    seen_ids = set()
    covered_routes = set()
    safe_routes = REQUIRED_ROUTES - {"premium-codex-claude"}

    for task in tasks:
        if not isinstance(task, dict):
            failures.append("task entries must be objects")
            continue

        task_id = str(task.get("id") or "unknown")
        if task_id in seen_ids:
            failures.append(f"duplicate task id: {task_id}")
        seen_ids.add(task_id)

        missing_fields = REQUIRED_TASK_FIELDS - set(task)
        if missing_fields:
            failures.append(f"task {task_id} missing fields: {sorted(missing_fields)}")

        expected_route = str(task.get("expected_route") or "")
        if expected_route not in routes:
            failures.append(f"task {task_id} references unknown route {expected_route!r}")
        else:
            covered_routes.add(expected_route)

        inferred = inferred_route(task)
        if inferred != expected_route:
            failures.append(
                f"task {task_id} expected {expected_route}, but policy infers {inferred}"
            )

        labels = set(_as_list(task.get("labels")))
        if not labels:
            failures.append(f"task {task_id} has no routing labels")
        unknown_labels = labels - REQUIRED_LABELS
        if unknown_labels:
            failures.append(f"task {task_id} has unknown labels: {sorted(unknown_labels)}")

        if expected_route == "premium-codex-claude" and "ai-risky" not in labels:
            failures.append(f"premium task {task_id} must include ai-risky")

        if expected_route in safe_routes and "ai-risky" in labels:
            failures.append(f"low-cost task {task_id} cannot include ai-risky")

        disallowed = {item.lower() for item in _as_list(task.get("disallowed_modes"))}
        if "--yolo" not in disallowed:
            failures.append(f"task {task_id} must disallow --yolo")
        if expected_route == "premium-codex-claude" and "low-cost-worker" not in disallowed:
            failures.append(f"premium task {task_id} must disallow low-cost-worker")

        if not _as_list(task.get("verification")):
            failures.append(f"task {task_id} needs at least one verification command")
        if not _as_list(task.get("success_criteria")):
            failures.append(f"task {task_id} needs success criteria")

    missing_coverage = REQUIRED_ROUTES - covered_routes
    if missing_coverage:
        failures.append(f"eval tasks do not cover routes: {sorted(missing_coverage)}")

    return failures


def iter_tasks(data: dict) -> Iterable[dict]:
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        return []
    return tasks


def _prompt_markdown(task: dict) -> str:
    lines = [
        f"# {task['id']}: {task['title']}",
        "",
        f"Expected route: `{task['expected_route']}`",
        f"Labels: `{', '.join(_as_list(task.get('labels')))}`",
        f"Risk level: `{task['risk_level']}`",
        "",
        "## Prompt",
        "",
        str(task["prompt"]),
        "",
        "## Surfaces",
        "",
    ]
    lines.extend(f"- `{surface}`" for surface in _as_list(task.get("surfaces")))
    lines.extend(["", "## Verification", ""])
    lines.extend(f"- `{command}`" for command in _as_list(task.get("verification")))
    lines.extend(["", "## Success Criteria", ""])
    lines.extend(f"- {item}" for item in _as_list(task.get("success_criteria")))
    lines.extend(["", "## Disallowed Modes", ""])
    lines.extend(f"- `{item}`" for item in _as_list(task.get("disallowed_modes")))
    lines.append("")
    return "\n".join(lines)


def export_prompts(data: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for task in iter_tasks(data):
        task_id = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(task["id"]))
        (output_dir / f"{task_id}.md").write_text(_prompt_markdown(task), encoding="utf-8")


def print_task_list(data: dict) -> None:
    for task in iter_tasks(data):
        print(
            f"{task['id']}: {task['expected_route']} "
            f"[{', '.join(_as_list(task.get('labels')))}]"
        )


def score_results(data: dict, results_path: Path) -> Tuple[int, int]:
    with results_path.open("r", encoding="utf-8") as handle:
        results = json.load(handle)
    if not isinstance(results, list):
        raise ValueError("results file must contain a list")

    valid_task_ids = {str(task["id"]) for task in iter_tasks(data)}
    passed = 0
    total = 0
    for result in results:
        if not isinstance(result, dict):
            raise ValueError("result entries must be objects")
        task_id = str(result.get("task_id") or "")
        if task_id not in valid_task_ids:
            raise ValueError(f"unknown task_id in results: {task_id}")
        total += 1
        if bool(result.get("passed")):
            passed += 1
    return passed, total


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument("--check", action="store_true", help="Validate the routing eval catalog.")
    parser.add_argument("--list", action="store_true", help="List routing eval tasks.")
    parser.add_argument(
        "--export-prompts",
        type=Path,
        help="Write one markdown prompt per eval task to this directory.",
    )
    parser.add_argument(
        "--score-results",
        type=Path,
        help="Score a JSON results file with task_id and passed fields.",
    )
    args = parser.parse_args(argv)

    data = load_config()
    failures = validate_config(data)
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1

    if args.list:
        print_task_list(data)

    if args.export_prompts:
        export_prompts(data, args.export_prompts)
        print(f"Exported prompts to {args.export_prompts}")

    if args.score_results:
        passed, total = score_results(data, args.score_results)
        print(f"Agent routing eval results: {passed}/{total} passed")

    if args.check or not (args.list or args.export_prompts or args.score_results):
        print(
            "Agent routing eval catalog is valid: "
            f"{len(list(iter_tasks(data)))} tasks, {len(data.get('routes', {}))} routes."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
