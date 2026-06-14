#!/usr/bin/env python3
"""Sync canonical skills into agent skill directories.

The canonical source of truth lives under skills/canonical/<skill-name>/.
By default this script performs a dry run and never deletes files.
Use --write to copy changed files into the requested target trees.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


TARGETS = {
    "claude": ".claude/skills",
    "codex": ".codex/skills",
    "agents": ".agents/skills",
    "repo": "skills/generated",
}

TARGET_CHOICES = ("claude", "codex", "agents", "repo", "all")


@dataclass(frozen=True)
class Action:
    kind: str
    source: Path
    destination: Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def canonical_root(root: Path) -> Path:
    return root / "skills" / "canonical"


def discover_skill_dirs(source_root: Path) -> list[Path]:
    if not source_root.exists():
        return []
    skill_dirs = [
        path
        for path in source_root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    ]
    return sorted(skill_dirs, key=lambda path: path.name.lower())


def resolve_targets(root: Path, target_name: str) -> list[tuple[str, Path]]:
    if target_name == "all":
        names = ("claude", "codex", "agents", "repo")
    else:
        names = (target_name,)
    return [(name, root / TARGETS[name]) for name in names]


def build_actions(source_root: Path, target_root: Path) -> list[Action]:
    actions: list[Action] = []
    for skill_dir in discover_skill_dirs(source_root):
        for source_file in sorted(
            (path for path in skill_dir.rglob("*") if path.is_file()),
            key=lambda path: path.relative_to(skill_dir).as_posix().lower(),
        ):
            relative = source_file.relative_to(skill_dir)
            destination = target_root / skill_dir.name / relative
            if not destination.exists():
                actions.append(Action("copy", source_file, destination))
                continue
            if destination.is_file() and not filecmp.cmp(source_file, destination, shallow=False):
                actions.append(Action("copy", source_file, destination))
    return actions


def print_plan(target_label: str, target_root: Path, actions: list[Action], write: bool) -> None:
    mode = "write" if write else "dry-run"
    print(f"[{mode}] target={target_label} path={target_root}")
    if not actions:
        print("  no changes")
        return
    for action in actions:
        print(f"  {action.kind}: {action.source.relative_to(repo_root())} -> {action.destination.relative_to(repo_root())}")


def apply_actions(actions: list[Action]) -> None:
    for action in actions:
        action.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(action.source, action.destination)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        choices=TARGET_CHOICES,
        default="all",
        help="Which destination tree to sync. Default: all",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Actually copy files. Without this flag, the script only prints the planned changes.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = repo_root()
    source_root = canonical_root(root)

    if not source_root.exists():
        print(f"Canonical skill root not found: {source_root}", file=sys.stderr)
        return 1

    targets = resolve_targets(root, args.target)
    all_actions: list[Action] = []
    for target_label, target_root in targets:
        actions = build_actions(source_root, target_root)
        print_plan(target_label, target_root, actions, args.write)
        all_actions.extend(actions)

    if not args.write:
        if all_actions:
            print(f"Pending sync actions: {len(all_actions)} file(s). Run with --write to apply.")
            return 1
        return 0

    apply_actions(all_actions)
    print(f"Completed copy of {len(all_actions)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
