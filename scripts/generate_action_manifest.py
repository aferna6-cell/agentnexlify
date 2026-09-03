#!/usr/bin/env python3
"""Generate a read-only Action tool manifest from the registered Action tools.

Does **not** import the Action Executor or tool execute functions. Parses
``toolRegistry.register(identifier)`` in ``registry.ts``, resolves each
identifier through a supported ``import { ident } from "./tools/....ts"``,
then reads ``defineTool({...})`` metadata plus constant aliases from
``flags.ts``.

Manifest IDs are exactly the registered Action tools — a ``tools/*.ts``
definition that is not registered is not planner-visible. Unsupported or
ambiguous registration/import shapes fail loudly.

Usage:
  python scripts/generate_action_manifest.py            # write manifest
  python scripts/generate_action_manifest.py --check    # exit 1 on drift
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIONS_DIR = ROOT / "agent-service" / "src" / "agent-os" / "actions"
TOOLS_DIR = ACTIONS_DIR / "tools"
REGISTRY_PATH = ACTIONS_DIR / "registry.ts"
FLAGS_PATH = ACTIONS_DIR / "flags.ts"
MANIFEST_PATH = ACTIONS_DIR / "action_manifest.json"

RISK_ALIASES = {
    "RISK_READ_ONLY": 0,
    "RISK_INTERNAL_MUTATION": 1,
    "RISK_EXTERNAL_COMMUNICATION": 2,
    "RISK_HIGH_IMPACT": 3,
}

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_IMPORT_RE = re.compile(
    r'import\s+\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\s+from\s+(["\'])'
    r'(\./tools/[^"\']+\.ts)\2\s*;',
    re.S,
)
_TOOLS_FROM_RE = re.compile(r"""from\s+(["'])(\./tools/[^"']+)\1""")
_REGISTER_OPEN_RE = re.compile(r"\btoolRegistry\.register\s*\(")
_REGISTER_GENERIC_RE = re.compile(r"\btoolRegistry\.register\s*<")
_DEFAULT_CTOR_RE = re.compile(
    r"export\s+const\s+toolRegistry\s*=\s*new\s+ToolRegistry\s*\("
)


def _load_flag_aliases(path: Path | None = None) -> dict[str, str]:
    text = (path or FLAGS_PATH).read_text(encoding="utf-8")
    aliases: dict[str, str] = {}
    for name, value in re.findall(
        r'export const ([A-Z0-9_]+)\s*=\s*"([^"]+)"', text
    ):
        aliases[name] = value
    return aliases


def _strip_ts_comments(text: str) -> str:
    """Remove // and /* */ comments without touching string literals."""
    out: list[str] = []
    i = 0
    n = len(text)
    state = "code"
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if state == "code":
            if ch == "/" and nxt == "/":
                state = "line"
                i += 2
                continue
            if ch == "/" and nxt == "*":
                state = "block"
                i += 2
                continue
            if ch == "'":
                state = "sq"
            elif ch == '"':
                state = "dq"
            elif ch == "`":
                state = "bt"
            out.append(ch)
            i += 1
            continue
        if state == "line":
            if ch == "\n":
                state = "code"
                out.append(ch)
            i += 1
            continue
        if state == "block":
            if ch == "*" and nxt == "/":
                state = "code"
                i += 2
                continue
            if ch == "\n":
                out.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            out.append(ch)
            out.append(text[i + 1])
            i += 2
            continue
        out.append(ch)
        if (state == "sq" and ch == "'") or (state == "dq" and ch == '"') or (
            state == "bt" and ch == "`"
        ):
            state = "code"
        i += 1
    if state == "block":
        raise ValueError("unterminated block comment in TypeScript source")
    return "".join(out)


def _read_paren_arg(text: str, inner_start: int) -> tuple[str, int]:
    """Read the inside of ``(...)`` starting after the opening paren."""
    depth = 1
    i = inner_start
    while i < len(text) and depth:
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        i += 1
    if depth != 0:
        raise ValueError("unclosed '(' in registry.ts")
    inner = text[inner_start : i - 1].strip()
    if inner.endswith(","):
        inner = inner[:-1].strip()
    return inner, i


def parse_registry_registrations(text: str) -> list[str]:
    """Return registered identifiers. Raises on unsupported register shapes."""
    cleaned = _strip_ts_comments(text)
    _assert_default_registry_ctor_empty(cleaned)
    if _REGISTER_GENERIC_RE.search(cleaned):
        raise ValueError(
            "unsupported generic toolRegistry.register<...>(...); "
            "only toolRegistry.register(identifier) is allowed"
        )
    names: list[str] = []
    seen: set[str] = set()
    for match in _REGISTER_OPEN_RE.finditer(cleaned):
        arg, _end = _read_paren_arg(cleaned, match.end())
        if not _IDENT_RE.fullmatch(arg):
            raise ValueError(
                f"unsupported toolRegistry.register() argument {arg!r}; "
                "only toolRegistry.register(identifier) is allowed"
            )
        if arg in seen:
            raise ValueError(f"duplicate toolRegistry.register({arg})")
        seen.add(arg)
        names.append(arg)
    return names


def _assert_default_registry_ctor_empty(text: str) -> None:
    matches = list(_DEFAULT_CTOR_RE.finditer(text))
    if not matches:
        raise ValueError(
            "registry.ts must export `const toolRegistry = new ToolRegistry()`"
        )
    if len(matches) > 1:
        raise ValueError("ambiguous export const toolRegistry = new ToolRegistry(")
    arg, _end = _read_paren_arg(text, matches[0].end())
    if arg:
        raise ValueError(
            "unsupported ToolRegistry constructor arguments; "
            "register tools with toolRegistry.register(identifier) only"
        )


def parse_registry_tool_imports(text: str) -> dict[str, str]:
    """Map identifier → ``./tools/<file>.ts``. Raises on unsupported imports."""
    cleaned = _strip_ts_comments(text)
    mapping: dict[str, str] = {}
    consumed: list[tuple[int, int]] = []
    for match in _IMPORT_RE.finditer(cleaned):
        ident, _quote, rel = match.group(1), match.group(2), match.group(3)
        if ident in mapping and mapping[ident] != rel:
            raise ValueError(
                f"ambiguous import for {ident}: {mapping[ident]} vs {rel}"
            )
        mapping[ident] = rel
        consumed.append(match.span())
    for match in _TOOLS_FROM_RE.finditer(cleaned):
        if any(start <= match.start() and match.end() <= end for start, end in consumed):
            continue
        raise ValueError(
            f"unsupported/ambiguous ./tools/ import shape: {match.group(0)!r}"
        )
    return mapping


def collect_registered_tool_files(
    registry_text: str, tools_dir: Path
) -> dict[str, Path]:
    """Map registered identifier → tool file path. Fail if unresolved."""
    idents = parse_registry_registrations(registry_text)
    imports = parse_registry_tool_imports(registry_text)
    if imports and not idents:
        raise ValueError(
            "registry imports ./tools/ modules but has no "
            "toolRegistry.register(identifier) calls"
        )
    resolved: dict[str, Path] = {}
    tools_root = tools_dir.resolve()
    for ident in idents:
        rel = imports.get(ident)
        if rel is None:
            raise ValueError(
                f"registered identifier {ident!r} has no supported "
                '`import { ident } from "./tools/....ts"`'
            )
        if (
            ".." in rel
            or not rel.startswith("./tools/")
            or not rel.endswith(".ts")
            or rel.endswith(".test.ts")
        ):
            raise ValueError(f"illegal tool import path {rel!r}")
        path = (tools_dir / rel.rsplit("/", 1)[-1]).resolve()
        if path.parent != tools_root:
            raise ValueError(f"tool import escapes tools dir: {rel}")
        if not path.is_file():
            raise ValueError(f"registered tool file missing: {rel}")
        resolved[ident] = path
    return resolved


def _extract_define_tool_block(text: str) -> str | None:
    match = re.search(r"defineTool\(\s*\{", text)
    if not match:
        return None
    start = match.end() - 1
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _field(block: str, name: str) -> str | None:
    m = re.search(rf"\b{name}\s*:\s*([^,\n]+)", block)
    if not m:
        return None
    return m.group(1).strip()


def parse_tool_file(path: Path, aliases: dict[str, str]) -> dict | None:
    text = path.read_text(encoding="utf-8")
    block = _extract_define_tool_block(text)
    if not block:
        return None

    raw_id = _field(block, "id")
    if not raw_id:
        return None
    tool_id = raw_id.strip().strip('"')
    if tool_id in aliases:
        tool_id = aliases[tool_id]

    raw_dept = _field(block, "department")
    department: str | None = None
    if raw_dept is not None:
        token = raw_dept.strip().strip('"')
        department = aliases.get(
            token, token if raw_dept.startswith('"') else aliases.get(token)
        )

    raw_risk = _field(block, "riskLevel")
    if raw_risk is None:
        raise ValueError(f"{path.name}: missing riskLevel")
    risk_token = raw_risk.strip()
    if risk_token not in RISK_ALIASES:
        raise ValueError(f"{path.name}: unknown riskLevel {risk_token}")
    risk_level = RISK_ALIASES[risk_token]

    raw_approval = _field(block, "requiresApproval")
    if raw_approval is None:
        raise ValueError(f"{path.name}: missing requiresApproval")
    requires_approval = raw_approval.strip() == "true"

    raw_mutating = _field(block, "mutating")
    mutating = raw_mutating.strip() == "true" if raw_mutating else False

    # verifiable iff the tool object declares a verify hook.
    verifiable = bool(re.search(r"\basync\s+verify\s*\(|\bverify\s*:\s*", block))

    return {
        "id": tool_id,
        "department": department,
        "risk_level": risk_level,
        "requires_approval": requires_approval,
        "mutating": mutating,
        "verifiable": verifiable,
    }


def build_manifest(
    *,
    tools_dir: Path | None = None,
    registry_path: Path | None = None,
    flags_path: Path | None = None,
) -> dict:
    tools_dir = tools_dir or TOOLS_DIR
    registry_path = registry_path or REGISTRY_PATH
    flags_path = flags_path or FLAGS_PATH
    if not registry_path.is_file():
        raise FileNotFoundError(f"missing Action registry: {registry_path}")
    aliases = _load_flag_aliases(flags_path)
    registry_text = registry_path.read_text(encoding="utf-8")
    registered_files = collect_registered_tool_files(registry_text, tools_dir)
    tools: dict[str, dict] = {}
    for ident, path in registered_files.items():
        parsed = parse_tool_file(path, aliases)
        if parsed is None:
            raise ValueError(
                f"registered tool {ident} ({path.name}) has no parseable "
                "defineTool({...})"
            )
        if parsed["id"] in tools:
            raise ValueError(f"duplicate tool id {parsed['id']}")
        tools[parsed["id"]] = parsed
    return {
        "_comment": (
            "Auto-generated by scripts/generate_action_manifest.py from "
            "registered Action tools in registry.ts plus defineTool metadata. "
            "Do not edit by hand — re-run the generator. Used for M9 planner "
            "catalog parity."
        ),
        "tools": tools,
    }


def registered_tool_ids(
    *,
    tools_dir: Path | None = None,
    registry_path: Path | None = None,
    flags_path: Path | None = None,
) -> list[str]:
    manifest = build_manifest(
        tools_dir=tools_dir,
        registry_path=registry_path,
        flags_path=flags_path,
    )
    return sorted(manifest["tools"])


def write_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def check_manifest(manifest: dict, manifest_path: Path | None = None) -> int:
    path = manifest_path or MANIFEST_PATH
    if not path.exists():
        print(f"MISSING: {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
        return 1
    current = json.loads(path.read_text(encoding="utf-8"))
    generated_ids = set((manifest.get("tools") or {}).keys())
    committed_ids = set((current.get("tools") or {}).keys())
    # Compare tool payloads only (ignore comment churn).
    if current.get("tools") != manifest.get("tools"):
        print("DRIFT: action_manifest.json does not match registered Action tools.")
        print("Run: python scripts/generate_action_manifest.py")
        if committed_ids != generated_ids:
            print(f"  id only in manifest: {sorted(committed_ids - generated_ids)}")
            print(f"  id only in registry: {sorted(generated_ids - committed_ids)}")
        for tid in sorted(committed_ids & generated_ids):
            if current["tools"][tid] != manifest["tools"][tid]:
                print(f"  changed: {tid}")
                print(f"    manifest: {current['tools'][tid]}")
                print(f"    source:   {manifest['tools'][tid]}")
        return 1
    print(
        f"OK: action_manifest.json matches {len(manifest['tools'])} "
        "registered Action tools."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if committed manifest drifts from registered Action tools",
    )
    args = parser.parse_args()
    manifest = build_manifest()
    if args.check:
        return check_manifest(manifest)
    write_manifest(manifest)
    print(
        f"Wrote {MANIFEST_PATH.relative_to(ROOT)} "
        f"({len(manifest['tools'])} registered Action tools)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
