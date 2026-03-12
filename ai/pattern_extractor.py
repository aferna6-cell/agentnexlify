import argparse
from collections import Counter, defaultdict

from .skill_creator import SkillCreator
from .task_memory import TaskMemory


class PatternExtractor:
    def __init__(
        self,
        memory: TaskMemory | None = None,
        creator: SkillCreator | None = None,
    ):
        self.memory = memory or TaskMemory()
        self.creator = creator or SkillCreator()

    def extract_patterns(self, min_occurrences: int = 2) -> dict:
        tasks = self.memory.load_tasks()
        workflow_counter = Counter()
        bug_counter = Counter()
        architecture_counter = Counter()
        refactor_counter = Counter()
        examples = defaultdict(list)

        for task in tasks:
            skills = tuple(sorted(task.get("skills_used", [])))
            if skills:
                workflow_counter[skills] += 1
                examples[("workflow", skills)].append(task["task_description"])

            for error in task.get("errors_encountered", []):
                bug_counter[error] += 1
                examples[("bug", error)].append(task["task_description"])

            if task.get("files_modified"):
                roots = tuple(sorted({path.split("/", 1)[0] for path in task["files_modified"]}))
                architecture_counter[roots] += 1
                examples[("architecture", roots)].append(task["task_description"])

            for fix in task.get("fixes_applied", []):
                refactor_counter[fix] += 1
                examples[("refactor", fix)].append(task["task_description"])

        return {
            "workflow_patterns": self._serialize_counter(
                workflow_counter, examples, "workflow", min_occurrences
            ),
            "bug_patterns": self._serialize_counter(
                bug_counter, examples, "bug", min_occurrences
            ),
            "architecture_patterns": self._serialize_counter(
                architecture_counter, examples, "architecture", min_occurrences
            ),
            "refactor_patterns": self._serialize_counter(
                refactor_counter, examples, "refactor", min_occurrences
            ),
        }

    def generate_skills_from_patterns(self, min_occurrences: int = 2) -> list[str]:
        patterns = self.extract_patterns(min_occurrences=min_occurrences)
        created = []

        for pattern in patterns["workflow_patterns"]:
            skill_name = "workflow-" + "-".join(pattern["label"].split(", "))
            try:
                created_path = self.creator.create_skill_from_pattern(
                    pattern_name=skill_name,
                    summary=(
                        "Generated from recurring task workflow involving skills: "
                        f"{pattern['label']}"
                    ),
                    examples=pattern["examples"],
                    workflow_steps=[
                        "Resolve the recurring skill set for the task.",
                        "Open the same file clusters that appeared in prior successful tasks.",
                        "Apply the deterministic workflow before introducing new patterns.",
                        "Record the outcome back into task memory.",
                    ],
                    created_by="auto-improve",
                )
                created.append(str(created_path))
            except FileExistsError:
                continue

        return created

    def persist_patterns(self, min_occurrences: int = 2) -> dict:
        patterns = self.extract_patterns(min_occurrences=min_occurrences)
        for pattern in patterns["bug_patterns"]:
            self.memory.record_bug_pattern(pattern["label"], pattern["examples"][0])
        for pattern in patterns["architecture_patterns"]:
            self.memory.record_architecture_pattern(pattern["label"], pattern["examples"][0])
        for pattern in patterns["refactor_patterns"]:
            self.memory.record_refactor_pattern(pattern["label"], pattern["examples"][0])
        return patterns

    def _serialize_counter(self, counter, examples, category: str, min_occurrences: int) -> list[dict]:
        serialized = []
        for key, count in counter.items():
            if count < min_occurrences:
                continue
            if isinstance(key, tuple):
                label = ", ".join(key)
            else:
                label = str(key)
            serialized.append(
                {
                    "category": category,
                    "label": label,
                    "count": count,
                    "examples": examples[(category, key)][:5],
                }
            )
        serialized.sort(key=lambda item: item["count"], reverse=True)
        return serialized


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract patterns from task memory.")
    parser.add_argument("--min-occurrences", type=int, default=2)
    parser.add_argument("--generate-skills", action="store_true")
    args = parser.parse_args()

    extractor = PatternExtractor()
    patterns = extractor.persist_patterns(min_occurrences=args.min_occurrences)
    if args.generate_skills:
        created = extractor.generate_skills_from_patterns(
            min_occurrences=args.min_occurrences
        )
        print({"patterns": patterns, "generated_skills": created})
    else:
        print(patterns)


if __name__ == "__main__":
    main()
