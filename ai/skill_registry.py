import argparse
import difflib
from datetime import datetime, timezone
from pathlib import Path

from . import DEFAULT_SKILL_ROOTS, SKILL_INDEX_PATH, first_nonempty_line, parse_frontmatter, read_json, relative_path, skill_source_from_path, tokenize, utc_now_iso, write_json


class SkillRegistry:
    def __init__(self, index_path: Path | None = None):
        self.index_path = index_path or SKILL_INDEX_PATH

    def load_index(self) -> dict:
        return read_json(
            self.index_path,
            {"schema_version": 1, "updated_at": None, "skills": []},
        )

    def discover_skill_files(self) -> list[Path]:
        discovered = []
        for root in DEFAULT_SKILL_ROOTS:
            if not root.exists():
                continue
            discovered.extend(root.glob("*/SKILL.md"))
        return sorted(set(path.resolve() for path in discovered))

    def _derive_tags(self, name: str, description: str, body: str) -> list[str]:
        ordered = []
        for token in tokenize(" ".join([name, description, body])):
            if token not in ordered:
                ordered.append(token)
        return ordered[:12]

    def _build_entry(self, skill_path: Path, existing: dict | None = None) -> dict:
        text = skill_path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(text)
        name = frontmatter.get("name") or skill_path.parent.name
        description = frontmatter.get("description") or first_nonempty_line(body)
        source = skill_source_from_path(skill_path)
        existing = existing or {}

        stat = skill_path.stat()
        inferred_created_at = datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).replace(microsecond=0).isoformat()

        return {
            "skill_name": name,
            "description": description,
            "tags": existing.get("tags") or self._derive_tags(name, description, body),
            "path": relative_path(skill_path),
            "created_by": existing.get("created_by")
            or frontmatter.get("created_by")
            or ("codex" if source == "generated" else "repository"),
            "created_at": existing.get("created_at") or inferred_created_at,
            "last_used": existing.get("last_used"),
            "source": source,
        }

    def rebuild_index(self) -> dict:
        current = self.load_index()
        existing_by_name = {
            skill["skill_name"]: skill for skill in current.get("skills", [])
        }

        skills = []
        for skill_path in self.discover_skill_files():
            frontmatter, _ = parse_frontmatter(skill_path.read_text(encoding="utf-8"))
            name = frontmatter.get("name") or skill_path.parent.name
            skills.append(self._build_entry(skill_path, existing_by_name.get(name)))

        skills.sort(key=lambda item: (item.get("source", "repository"), item["skill_name"]))
        index = {
            "schema_version": 1,
            "updated_at": utc_now_iso(),
            "skills": skills,
        }
        write_json(self.index_path, index)
        return index

    def list_skills(self, source: str | None = None) -> list[dict]:
        skills = self.load_index().get("skills", [])
        if source:
            return [skill for skill in skills if skill.get("source") == source]
        return skills

    def search(
        self,
        query: str,
        tags: list[str] | None = None,
        limit: int = 5,
        source: str | None = None,
    ) -> list[dict]:
        tags = [tag.lower() for tag in (tags or [])]
        query_tokens = set(tokenize(query))
        results = []
        for skill in self.list_skills(source=source):
            haystack = " ".join(
                [
                    skill.get("skill_name", ""),
                    skill.get("description", ""),
                    " ".join(skill.get("tags", [])),
                ]
            ).lower()
            name = skill.get("skill_name", "").lower()
            score = 0.0

            if query and query.lower() in name:
                score += 5.0
            elif query and query.lower() in haystack:
                score += 2.5

            overlap = len(query_tokens & set(tokenize(haystack)))
            score += overlap * 1.5

            if tags:
                tag_overlap = len(set(tags) & set(skill.get("tags", [])))
                score += tag_overlap * 2.0

            if query:
                score += difflib.SequenceMatcher(None, query.lower(), name).ratio()

            if score <= 0:
                continue

            results.append({**skill, "score": round(score, 3)})

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:limit]

    def find(self, skill_name: str) -> dict | None:
        for skill in self.list_skills():
            if skill.get("skill_name") == skill_name:
                return skill
        return None

    def mark_used(self, skill_name: str, when: str | None = None) -> dict:
        index = self.load_index()
        for skill in index.get("skills", []):
            if skill.get("skill_name") == skill_name:
                skill["last_used"] = when or utc_now_iso()
                write_json(self.index_path, index)
                return skill
        raise KeyError(f"Skill not found: {skill_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the AgentNexLiFy skill registry.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("rebuild", help="Rebuild skills/index.json from repo skills.")

    search_parser = subparsers.add_parser("search", help="Search indexed skills.")
    search_parser.add_argument("query", help="Task or skill query.")
    search_parser.add_argument("--tags", nargs="*", default=[], help="Optional tags.")
    search_parser.add_argument("--limit", type=int, default=5, help="Maximum results.")
    search_parser.add_argument("--source", choices=["repository", "generated"], help="Filter by source.")

    mark_parser = subparsers.add_parser("mark-used", help="Update a skill's last_used timestamp.")
    mark_parser.add_argument("skill_name", help="Exact skill name.")

    list_parser = subparsers.add_parser("list", help="List indexed skills.")
    list_parser.add_argument("--source", choices=["repository", "generated"], help="Filter by source.")

    args = parser.parse_args()
    registry = SkillRegistry()

    if args.command == "rebuild":
        print(registry.rebuild_index())
    elif args.command == "search":
        print(registry.search(args.query, tags=args.tags, limit=args.limit, source=args.source))
    elif args.command == "mark-used":
        print(registry.mark_used(args.skill_name))
    elif args.command == "list":
        print(registry.list_skills(source=args.source))


if __name__ == "__main__":
    main()
