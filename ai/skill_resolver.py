import argparse

from .skill_creator import SkillCreator
from .skill_registry import SkillRegistry
from .skill_search import SkillSearch


class SkillResolver:
    def __init__(
        self,
        registry: SkillRegistry | None = None,
        search: SkillSearch | None = None,
        creator: SkillCreator | None = None,
    ):
        self.registry = registry or SkillRegistry()
        self.search = search or SkillSearch()
        self.creator = creator or SkillCreator(registry=self.registry)

    def resolve_skills(
        self,
        task_description: str,
        limit: int = 5,
        auto_generate: bool = False,
        allow_external: bool = True,
    ) -> dict:
        repository_matches = self.registry.search(
            task_description, limit=limit, source="repository"
        )
        generated_matches = self.registry.search(
            task_description, limit=limit, source="generated"
        )

        selected = repository_matches[:]
        if len(selected) < limit:
            for match in generated_matches:
                if match["skill_name"] not in {item["skill_name"] for item in selected}:
                    selected.append(match)
                if len(selected) >= limit:
                    break

        external_patterns = []
        if allow_external and not selected:
            external_patterns = self.search.search_external_workflows(
                task_description, max_results=3
            )

        generated_skill = None
        if auto_generate and not selected and not generated_matches:
            generated_skill = self.creator.create_skill_from_task(
                task_description, created_by="resolver"
            )
            self.registry.rebuild_index()
            selected = self.registry.search(task_description, limit=limit)

        return {
            "task_description": task_description,
            "selected_skills": selected[:limit],
            "repository_matches": repository_matches,
            "generated_matches": generated_matches,
            "external_patterns": external_patterns,
            "generated_skill": str(generated_skill) if generated_skill else None,
            "priority_order": [
                "repository_skills",
                "generated_skills",
                "external_patterns",
                "new_skill_generation",
            ],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve the best skills for a task.")
    parser.add_argument("task_description", help="Task description.")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--auto-generate", action="store_true")
    parser.add_argument("--no-external", action="store_true")
    args = parser.parse_args()

    resolver = SkillResolver()
    print(
        resolver.resolve_skills(
            args.task_description,
            limit=args.limit,
            auto_generate=args.auto_generate,
            allow_external=not args.no_external,
        )
    )


if __name__ == "__main__":
    main()
