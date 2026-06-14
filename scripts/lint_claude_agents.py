#!/usr/bin/env python3
"""Lint .claude/agents/*.md frontmatter (agnix-style).

Validates:
- name: required, must match filename stem
- description: required, <=500 chars (CLAUDE.md guidance: short triggers)
- model: optional, must be one of {sonnet, opus, haiku} or full model id
- tools: optional, must be list
- maxTurns: optional, must be int

Exit code 0 if all agents valid; 1 if any errors; 2 on missing dir.
"""
import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
ALLOWED_MODELS = {"sonnet", "opus", "haiku", "inherit"}
ALLOWED_MODEL_PREFIXES = ("claude-",)


def parse_frontmatter(text: str) -> dict | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    block = m.group(1)
    out: dict = {}
    current_key = None
    current_list: list | None = None
    for line in block.splitlines():
        if not line.strip():
            continue
        if line.startswith(" ") or line.startswith("\t"):
            stripped = line.strip()
            if stripped.startswith("- ") and current_list is not None:
                val = stripped[2:].strip().strip('"').strip("'")
                current_list.append(val)
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                current_list = []
                out[key] = current_list
                current_key = key
            elif val.startswith("[") and val.endswith("]"):
                inner = val[1:-1]
                items = [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()]
                out[key] = items
                current_list = None
                current_key = key
            else:
                out[key] = val.strip('"').strip("'")
                current_list = None
                current_key = key
    return out


def lint_agent(path: Path) -> list[str]:
    errs: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)
    if fm is None:
        errs.append("missing or malformed frontmatter")
        return errs

    name = fm.get("name")
    if not name:
        errs.append("missing 'name'")
    elif name != path.stem:
        errs.append(f"name '{name}' != filename stem '{path.stem}'")

    desc = fm.get("description")
    if not desc:
        errs.append("missing 'description'")
    elif len(desc) > 500:
        errs.append(f"description too long ({len(desc)} chars > 500)")

    model = fm.get("model")
    if model is not None:
        if model not in ALLOWED_MODELS and not str(model).startswith(ALLOWED_MODEL_PREFIXES):
            errs.append(f"unknown model '{model}'")

    tools = fm.get("tools")
    if tools is not None and not isinstance(tools, list):
        errs.append("'tools' must be a list")

    max_turns = fm.get("maxTurns")
    if max_turns is not None:
        try:
            int(max_turns)
        except (TypeError, ValueError):
            errs.append(f"'maxTurns' not int: {max_turns}")

    body = FRONTMATTER_RE.sub("", text, count=1).strip()
    if len(body) < 50:
        errs.append(f"system prompt too short ({len(body)} chars)")

    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not AGENTS_DIR.is_dir():
        print(f"ERR: {AGENTS_DIR} not found", file=sys.stderr)
        return 2

    total = 0
    failed = 0
    for md in sorted(AGENTS_DIR.glob("*.md")):
        total += 1
        errs = lint_agent(md)
        if errs:
            failed += 1
            print(f"FAIL {md.name}")
            for e in errs:
                print(f"  - {e}")
        elif not args.quiet:
            print(f"OK   {md.name}")

    print()
    print(f"Total agents: {total}")
    print(f"Failed:       {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
