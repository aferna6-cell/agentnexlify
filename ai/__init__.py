import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AI_DIR = REPO_ROOT / "ai"
MEMORY_DIR = AI_DIR / "memory"
SKILLS_DIR = REPO_ROOT / "skills"
GENERATED_SKILLS_DIR = SKILLS_DIR / "generated"
SKILL_INDEX_PATH = SKILLS_DIR / "index.json"
SKILL_SCHEMA_PATH = SKILLS_DIR / "schema.md"
TASK_HISTORY_PATH = MEMORY_DIR / "task_history.json"
BUG_PATTERNS_PATH = MEMORY_DIR / "bug_patterns.json"
ARCHITECTURE_PATTERNS_PATH = MEMORY_DIR / "architecture_patterns.json"
REFACTOR_PATTERNS_PATH = MEMORY_DIR / "refactor_patterns.json"
DEFAULT_SKILL_ROOTS = [
    REPO_ROOT / ".codex" / "skills",
    REPO_ROOT / ".claude" / "skills",
    GENERATED_SKILLS_DIR,
]
IGNORED_PATH_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "use",
    "when",
    "with",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, data) -> None:
    ensure_directory(path.parent)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9_\-]+", (text or "").lower())
    return [token for token in tokens if token not in STOPWORDS]


def slugify(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return normalized or "generated-skill"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text

    lines = text.splitlines()
    frontmatter_lines = []
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body = "\n".join(lines[index + 1 :])
            frontmatter = {}
            for item in frontmatter_lines:
                if ":" not in item:
                    continue
                key, value = item.split(":", 1)
                frontmatter[key.strip()] = value.strip().strip('"').strip("'")
            return frontmatter, body
        frontmatter_lines.append(line)

    return {}, text


def first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped.lstrip("#").strip()
    return ""


def skill_source_from_path(path: Path) -> str:
    relative = relative_path(path).replace("\\", "/")
    if relative.startswith("skills/generated/"):
        return "generated"
    return "repository"


def is_ignored_path(path: Path) -> bool:
    return bool(set(path.parts) & IGNORED_PATH_PARTS)
