import argparse

from .evaluation_engine import EvaluationEngine
from .pattern_extractor import PatternExtractor
from .skill_creator import SkillCreator
from .skill_registry import SkillRegistry
from .skill_resolver import SkillResolver
from .task_memory import TaskMemory


class AutonomousSkillEngine:
    def __init__(self):
        self.registry = SkillRegistry()
        self.memory = TaskMemory()
        self.creator = SkillCreator(registry=self.registry)
        self.resolver = SkillResolver(
            registry=self.registry,
            creator=self.creator,
        )
        self.evaluator = EvaluationEngine(
            memory=self.memory,
            registry=self.registry,
        )
        self.pattern_extractor = PatternExtractor(
            memory=self.memory,
            creator=self.creator,
        )

    def prepare_task(self, task_description: str, auto_generate: bool = False) -> dict:
        self.registry.rebuild_index()
        return self.resolver.resolve_skills(
            task_description,
            auto_generate=auto_generate,
        )

    def complete_task(
        self,
        task_description: str,
        skills_used: list[str],
        files_modified: list[str],
        errors_encountered: list[str],
        fixes_applied: list[str],
        outcome: str,
        generated_skills: list[str] | None = None,
    ) -> dict:
        return self.evaluator.evaluate_task(
            task_description=task_description,
            skills_used=skills_used,
            files_modified=files_modified,
            errors_encountered=errors_encountered,
            fixes_applied=fixes_applied,
            outcome=outcome,
            generated_skills=generated_skills or [],
        )

    def learn_from_history(self, min_occurrences: int = 2) -> dict:
        patterns = self.pattern_extractor.persist_patterns(
            min_occurrences=min_occurrences
        )
        generated_skills = self.pattern_extractor.generate_skills_from_patterns(
            min_occurrences=min_occurrences
        )
        return {
            "patterns": patterns,
            "generated_skills": generated_skills,
        }


def _split_csv(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Operate the autonomous AgentNexLiFy skill engine.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Resolve skills for a task.")
    prepare.add_argument("task_description")
    prepare.add_argument("--auto-generate", action="store_true")

    complete = subparsers.add_parser("complete", help="Record a completed task.")
    complete.add_argument("task_description")
    complete.add_argument("--skills-used", default="")
    complete.add_argument("--files-modified", default="")
    complete.add_argument("--errors", default="")
    complete.add_argument("--fixes", default="")
    complete.add_argument("--generated-skills", default="")
    complete.add_argument("--outcome", default="success")

    learn = subparsers.add_parser("learn", help="Extract patterns and generate reusable skills.")
    learn.add_argument("--min-occurrences", type=int, default=2)

    args = parser.parse_args()
    engine = AutonomousSkillEngine()

    if args.command == "prepare":
        print(engine.prepare_task(args.task_description, auto_generate=args.auto_generate))
    elif args.command == "complete":
        print(
            engine.complete_task(
                task_description=args.task_description,
                skills_used=_split_csv(args.skills_used),
                files_modified=_split_csv(args.files_modified),
                errors_encountered=_split_csv(args.errors),
                fixes_applied=_split_csv(args.fixes),
                outcome=args.outcome,
                generated_skills=_split_csv(args.generated_skills),
            )
        )
    elif args.command == "learn":
        print(engine.learn_from_history(min_occurrences=args.min_occurrences))


if __name__ == "__main__":
    main()
