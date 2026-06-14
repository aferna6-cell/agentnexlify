"""Validate skill metadata and obvious skill-packaging issues.

This checker is intentionally stdlib-only so it can run anywhere, including
Windows PowerShell shells, without extra setup.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOTS = (
    ROOT / ".claude" / "skills",
    ROOT / ".codex" / "skills",
    ROOT / ".agents" / "skills",
    ROOT / "skills" / "canonical",
    ROOT / "skills" / "generated",
)

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SIDE_EFFECT_RE = re.compile(
    r"\b(commit|push|deploy|ship|release|publish|merge|promote|rollback)\b",
    re.IGNORECASE,
)
DESCRIPTION_CUE_RE = re.compile(
    r"\b(use|when|before|after|while|whenever|trigger|any time|pre-deploy|preflight)\b",
    re.IGNORECASE,
)
REQUIRED_CANONICAL_HEADINGS = {
    "When to Use": re.compile(r"(?im)^##\s+When to Use\b"),
    "When NOT to Use": re.compile(r"(?im)^##\s+When NOT to Use\b"),
    "Read First": re.compile(r"(?im)^##\s+Read First\b"),
    "Workflow": re.compile(r"(?im)^##\s+Workflow\b"),
    "Output Format": re.compile(r"(?im)^##\s+Output Format\b"),
    "Constraints": re.compile(r"(?im)^##\s+Constraints\b"),
    "Examples": re.compile(r"(?im)^##\s+Examples\b"),
}
LOCAL_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_/.-])(?:\.?/)?(?:scripts|references|resources|assets)/[A-Za-z0-9_./-]+"
)
SECRET_RE = re.compile(
    r"\b(?:sk-(?:live|test|ant)-[A-Za-z0-9_-]{12,}|rk_live_[A-Za-z0-9_]{12,})\b",
    re.IGNORECASE,
)
LOCAL_PREFIXES = {"scripts", "references", "resources", "assets"}


@dataclass
class SkillDoc:
    path: Path
    root: Path
    frontmatter: dict[str, object]
    body: str
    body_start_line: int


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_frontmatter(text: str, path: Path) -> tuple[dict[str, object], str, int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing YAML frontmatter")

    fm_lines: list[str] = []
    end_index = None
    for idx in range(1, len(lines)):
        stripped = lines[idx].strip()
        if stripped == "---":
            end_index = idx
            break
        fm_lines.append(lines[idx])

    if end_index is None:
        raise ValueError("unterminated YAML frontmatter")

    frontmatter: dict[str, object] = {}
    for raw_line in fm_lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]
        lowered = value.lower()
        if lowered == "true":
            parsed: object = True
        elif lowered == "false":
            parsed = False
        elif lowered == "null" or lowered == "none":
            parsed = None
        else:
            parsed = value
        frontmatter[key] = parsed

    body = "\n".join(lines[end_index + 1 :])
    body_start_line = end_index + 2  # 1-based line number of the first body line
    return frontmatter, body, body_start_line


def skill_files() -> list[Path]:
    files: list[Path] = []
    for root in SKILL_ROOTS:
        if root.is_dir():
            files.extend(sorted(root.rglob("SKILL.md")))
    return sorted(files)


def normalize_key(key: str) -> str:
    return key.replace("_", "-").lower()


def frontmatter_flag(frontmatter: dict[str, object], *names: str) -> bool | None:
    wanted = {normalize_key(name) for name in names}
    for key, value in frontmatter.items():
        if normalize_key(key) in wanted:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "yes", "1"}:
                    return True
                if lowered in {"false", "no", "0"}:
                    return False
    return None


def skill_name(path: Path) -> str:
    return path.parent.name


def description_is_specific(description: str) -> bool:
    text = description.strip()
    if DESCRIPTION_CUE_RE.search(text):
        return True
    if len(text.split()) >= 12:
        return True
    return False


def file_line_for_token(body: str, token: str, start_line: int) -> int | None:
    for offset, line in enumerate(body.splitlines(), start=0):
        if token in line:
            return start_line + offset
    return None


def gather_local_paths(body: str) -> list[str]:
    seen: list[str] = []
    for match in LOCAL_PATH_RE.finditer(body):
        token = match.group(0).rstrip(").,;:'\"`")
        if token not in seen:
            seen.append(token)
    return seen


def main() -> int:
    hard_errors: list[str] = []
    warnings: list[str] = []
    scanned = skill_files()

    if not scanned:
        print("WARN no skill files found under configured roots")
        return 0

    for path in scanned:
        root = next((candidate for candidate in SKILL_ROOTS if candidate in path.parents), None)
        if root is None:
            continue

        try:
            frontmatter, body, body_start_line = parse_frontmatter(read_text(path), path)
        except ValueError as exc:
            hard_errors.append(f"{path}: {exc}")
            continue

        name = frontmatter.get("name")
        description = frontmatter.get("description")
        skill_dir_name = skill_name(path)
        rel_path = path.relative_to(ROOT)

        if name is None:
            hard_errors.append(f"{rel_path}: missing frontmatter name")
        elif not isinstance(name, str):
            hard_errors.append(f"{rel_path}: frontmatter name must be a string")
        else:
            if len(name) > 64:
                hard_errors.append(f"{rel_path}: name exceeds 64 characters ({len(name)})")
            if not NAME_RE.fullmatch(name):
                hard_errors.append(
                    f"{rel_path}: name must be lowercase kebab-case with digits allowed ({name!r})"
                )
            if skill_dir_name.lower() != name.lower():
                warnings.append(
                    f"{rel_path}: directory basename {skill_dir_name!r} does not match name {name!r}"
                )

        if description is None:
            hard_errors.append(f"{rel_path}: missing frontmatter description")
        elif not isinstance(description, str):
            hard_errors.append(f"{rel_path}: frontmatter description must be a string")
        elif not description_is_specific(description):
            warnings.append(
                f"{rel_path}: description may be too generic; add an explicit use/when cue or more concrete wording"
            )

        is_canonical = root == ROOT / "skills" / "canonical"
        if is_canonical:
            if "triggers" not in frontmatter:
                hard_errors.append(f"{rel_path}: canonical skill must define triggers")
            if isinstance(description, str) and not description.strip().lower().startswith("use when"):
                hard_errors.append(f"{rel_path}: canonical description must start with 'Use when'")
            for heading, pattern in REQUIRED_CANONICAL_HEADINGS.items():
                if not pattern.search(body):
                    hard_errors.append(f"{rel_path}: canonical skill missing '## {heading}' section")

        disable_flag = frontmatter_flag(frontmatter, "disable-model-invocation", "disable_model_invocation")
        if isinstance(name, str) and isinstance(description, str) and SIDE_EFFECT_RE.search(
            f"{name} {description}"
        ):
            if disable_flag is not True:
                hard_errors.append(
                    f"{rel_path}: side-effect skill should set disable-model-invocation: true"
                )

        body_lines = body.splitlines()
        if len(body_lines) > 500:
            warnings.append(f"{rel_path}: SKILL.md body exceeds 500 lines ({len(body_lines)})")
        elif len(body_lines) > 450:
            warnings.append(f"{rel_path}: SKILL.md body is long ({len(body_lines)} lines)")

        for match in SECRET_RE.finditer(body):
            hard_errors.append(
                f"{rel_path}: possible secret token pattern found in body ({match.group(0)})"
            )

        for token in gather_local_paths(body):
            if token.startswith("http://") or token.startswith("https://"):
                continue
            top_level = token.split("/", 1)[0]
            if top_level not in LOCAL_PREFIXES:
                continue
            if not (path.parent / top_level).exists():
                continue
            local_target = (path.parent / token).resolve()
            if not local_target.exists():
                line_no = file_line_for_token(body, token, body_start_line)
                location = f"{rel_path}:{line_no}" if line_no else str(rel_path)
                warnings.append(f"{location}: referenced local path does not exist: {token}")

    for warning in warnings:
        print(f"WARN {warning}")
    for error in hard_errors:
        print(f"FAIL {error}")

    print("")
    print(f"Scanned {len(scanned)} skill files.")
    print(f"Warnings: {len(warnings)}")
    print(f"Errors: {len(hard_errors)}")

    return 1 if hard_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
