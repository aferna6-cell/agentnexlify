import argparse

from . import ARCHITECTURE_PATTERNS_PATH, BUG_PATTERNS_PATH, MEMORY_DIR, REFACTOR_PATTERNS_PATH, TASK_HISTORY_PATH, ensure_directory, read_json, utc_now_iso, write_json


class TaskMemory:
    def __init__(self):
        ensure_directory(MEMORY_DIR)
        self._ensure_files()

    def _ensure_files(self) -> None:
        defaults = {
            TASK_HISTORY_PATH: {"schema_version": 1, "tasks": []},
            BUG_PATTERNS_PATH: {"schema_version": 1, "patterns": []},
            ARCHITECTURE_PATTERNS_PATH: {"schema_version": 1, "patterns": []},
            REFACTOR_PATTERNS_PATH: {"schema_version": 1, "patterns": []},
        }
        for path, default in defaults.items():
            if not path.exists():
                write_json(path, default)

    def load_tasks(self) -> list[dict]:
        return read_json(TASK_HISTORY_PATH, {"schema_version": 1, "tasks": []}).get("tasks", [])

    def record_task(
        self,
        task_description: str,
        skills_used: list[str],
        files_modified: list[str],
        errors_encountered: list[str],
        fixes_applied: list[str],
        outcome: str,
        generated_skills: list[str] | None = None,
        evaluation: dict | None = None,
        timestamp: str | None = None,
    ) -> dict:
        payload = read_json(TASK_HISTORY_PATH, {"schema_version": 1, "tasks": []})
        record = {
            "task_description": task_description,
            "skills_used": skills_used,
            "files_modified": files_modified,
            "errors_encountered": errors_encountered,
            "fixes_applied": fixes_applied,
            "outcome": outcome,
            "generated_skills": generated_skills or [],
            "evaluation": evaluation or {},
            "timestamp": timestamp or utc_now_iso(),
        }
        payload.setdefault("tasks", []).append(record)
        write_json(TASK_HISTORY_PATH, payload)
        return record

    def _record_pattern(self, path, pattern: str, category: str, example: str | None = None) -> dict:
        payload = read_json(path, {"schema_version": 1, "patterns": []})
        patterns = payload.setdefault("patterns", [])
        for item in patterns:
            if item.get("pattern") == pattern:
                item["count"] = item.get("count", 0) + 1
                item["last_seen"] = utc_now_iso()
                if example:
                    item.setdefault("examples", [])
                    if example not in item["examples"]:
                        item["examples"].append(example)
                write_json(path, payload)
                return item

        entry = {
            "pattern": pattern,
            "category": category,
            "count": 1,
            "examples": [example] if example else [],
            "first_seen": utc_now_iso(),
            "last_seen": utc_now_iso(),
        }
        patterns.append(entry)
        write_json(path, payload)
        return entry

    def record_bug_pattern(self, pattern: str, example: str | None = None) -> dict:
        return self._record_pattern(BUG_PATTERNS_PATH, pattern, "bug", example)

    def record_architecture_pattern(self, pattern: str, example: str | None = None) -> dict:
        return self._record_pattern(ARCHITECTURE_PATTERNS_PATH, pattern, "architecture", example)

    def record_refactor_pattern(self, pattern: str, example: str | None = None) -> dict:
        return self._record_pattern(REFACTOR_PATTERNS_PATH, pattern, "refactor", example)

    def summary(self) -> dict:
        return {
            "tasks_recorded": len(self.load_tasks()),
            "bug_patterns": len(read_json(BUG_PATTERNS_PATH, {"patterns": []}).get("patterns", [])),
            "architecture_patterns": len(
                read_json(ARCHITECTURE_PATTERNS_PATH, {"patterns": []}).get("patterns", [])
            ),
            "refactor_patterns": len(
                read_json(REFACTOR_PATTERNS_PATH, {"patterns": []}).get("patterns", [])
            ),
        }


def _split_csv(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Record and inspect autonomous task memory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_task = subparsers.add_parser("add-task", help="Append a task record to memory.")
    add_task.add_argument("task_description")
    add_task.add_argument("--skills-used", default="")
    add_task.add_argument("--files-modified", default="")
    add_task.add_argument("--errors", default="")
    add_task.add_argument("--fixes", default="")
    add_task.add_argument("--outcome", default="success")
    add_task.add_argument("--generated-skills", default="")

    add_bug = subparsers.add_parser("add-bug", help="Record a recurring bug pattern.")
    add_bug.add_argument("pattern")
    add_bug.add_argument("--example", default="")

    subparsers.add_parser("summary", help="Print memory summary.")

    args = parser.parse_args()
    memory = TaskMemory()

    if args.command == "add-task":
        print(
            memory.record_task(
                task_description=args.task_description,
                skills_used=_split_csv(args.skills_used),
                files_modified=_split_csv(args.files_modified),
                errors_encountered=_split_csv(args.errors),
                fixes_applied=_split_csv(args.fixes),
                outcome=args.outcome,
                generated_skills=_split_csv(args.generated_skills),
            )
        )
    elif args.command == "add-bug":
        print(memory.record_bug_pattern(args.pattern, args.example or None))
    elif args.command == "summary":
        print(memory.summary())


if __name__ == "__main__":
    main()
