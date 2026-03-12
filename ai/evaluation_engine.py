import argparse

from .skill_registry import SkillRegistry
from .task_memory import TaskMemory


class EvaluationEngine:
    def __init__(
        self,
        memory: TaskMemory | None = None,
        registry: SkillRegistry | None = None,
    ):
        self.memory = memory or TaskMemory()
        self.registry = registry or SkillRegistry()

    def evaluate_task(
        self,
        task_description: str,
        skills_used: list[str],
        files_modified: list[str],
        errors_encountered: list[str],
        fixes_applied: list[str],
        outcome: str,
        generated_skills: list[str] | None = None,
    ) -> dict:
        normalized_outcome = (outcome or "").lower()
        success = normalized_outcome in {"success", "completed", "fixed", "passed"}
        if errors_encountered and normalized_outcome not in {"success", "completed", "fixed"}:
            success = False

        evaluation = {
            "success": success,
            "error_count": len(errors_encountered),
            "generated_skill_count": len(generated_skills or []),
            "skill_failure": bool(errors_encountered and skills_used and not success),
        }

        record = self.memory.record_task(
            task_description=task_description,
            skills_used=skills_used,
            files_modified=files_modified,
            errors_encountered=errors_encountered,
            fixes_applied=fixes_applied,
            outcome=outcome,
            generated_skills=generated_skills or [],
            evaluation=evaluation,
        )

        for skill_name in skills_used:
            try:
                self.registry.mark_used(skill_name)
            except KeyError:
                continue

        for error in errors_encountered:
            self.memory.record_bug_pattern(error, task_description)
        for fix in fixes_applied:
            self.memory.record_refactor_pattern(fix, task_description)
        if files_modified:
            roots = ", ".join(sorted({path.split("/", 1)[0] for path in files_modified}))
            self.memory.record_architecture_pattern(
                f"task touched: {roots}", task_description
            )

        return {"record": record, "evaluation": evaluation}


def _split_csv(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate and record a completed task.")
    parser.add_argument("task_description")
    parser.add_argument("--skills-used", default="")
    parser.add_argument("--files-modified", default="")
    parser.add_argument("--errors", default="")
    parser.add_argument("--fixes", default="")
    parser.add_argument("--generated-skills", default="")
    parser.add_argument("--outcome", default="success")
    args = parser.parse_args()

    engine = EvaluationEngine()
    print(
        engine.evaluate_task(
            task_description=args.task_description,
            skills_used=_split_csv(args.skills_used),
            files_modified=_split_csv(args.files_modified),
            errors_encountered=_split_csv(args.errors),
            fixes_applied=_split_csv(args.fixes),
            outcome=args.outcome,
            generated_skills=_split_csv(args.generated_skills),
        )
    )


if __name__ == "__main__":
    main()
