import argparse
from pathlib import Path

from . import GENERATED_SKILLS_DIR, SKILL_SCHEMA_PATH, ensure_directory, slugify, tokenize, utc_now_iso
from .skill_registry import SkillRegistry


class SkillCreator:
    def __init__(self, output_dir: Path | None = None, registry: SkillRegistry | None = None):
        self.output_dir = output_dir or GENERATED_SKILLS_DIR
        self.registry = registry or SkillRegistry()
        ensure_directory(self.output_dir)

    def _serialize_list(self, values: list[str]) -> str:
        return "\n".join(f"- {value}" for value in values)

    def create_skill(
        self,
        name: str,
        purpose: str,
        when_to_use: list[str],
        inputs: list[str],
        workflow_steps: list[str],
        constraints: list[str],
        examples: list[str],
        created_by: str = "codex",
        overwrite: bool = False,
    ) -> Path:
        skill_dir = self.output_dir / slugify(name)
        ensure_directory(skill_dir)
        skill_path = skill_dir / "SKILL.md"

        if skill_path.exists() and not overwrite:
            raise FileExistsError(f"Skill already exists: {skill_path}")

        description = purpose.strip().rstrip(".")
        if len(description) > 180:
            description = description[:177].rstrip() + "..."

        content = (
            "---\n"
            f"name: {name}\n"
            f"description: {description}\n"
            f"created_by: {created_by}\n"
            "---\n\n"
            f"# {name}\n\n"
            "## Purpose\n"
            f"{purpose.strip()}\n\n"
            "## When To Use\n"
            f"{self._serialize_list(when_to_use)}\n\n"
            "## Inputs\n"
            f"{self._serialize_list(inputs)}\n\n"
            "## Workflow Steps\n"
            f"{self._serialize_list(workflow_steps)}\n\n"
            "## Constraints\n"
            f"{self._serialize_list(constraints)}\n\n"
            "## Examples\n"
            f"{self._serialize_list(examples)}\n"
        )
        skill_path.write_text(content, encoding="utf-8")
        self.registry.rebuild_index()
        return skill_path

    def create_skill_from_task(
        self,
        task_description: str,
        created_by: str = "codex",
        overwrite: bool = False,
    ) -> Path:
        tokens = tokenize(task_description)
        primary = tokens[:4] or ["task"]
        name = "generated-" + "-".join(primary)
        purpose = (
            "Deterministic workflow generated from a previously unseen task pattern: "
            f"{task_description.strip()}"
        )
        when_to_use = [
            f"Use when the task is substantially similar to: {task_description.strip()}",
            "Use when repository and generated skills do not already cover the workflow.",
        ]
        inputs = [
            "task_description",
            "relevant repository files",
            "current constraints and acceptance criteria",
        ]
        workflow_steps = self._workflow_from_keywords(task_description)
        constraints = [
            "Prefer existing repository conventions before introducing new patterns.",
            "Keep the workflow deterministic and reusable across similar tasks.",
            "Do not change production secrets, credentials, or schema without an explicit migration.",
        ]
        examples = [
            task_description.strip(),
            f"Repeatable variant of: {task_description.strip()}",
        ]

        return self.create_skill(
            name=name,
            purpose=purpose,
            when_to_use=when_to_use,
            inputs=inputs,
            workflow_steps=workflow_steps,
            constraints=constraints,
            examples=examples,
            created_by=created_by,
            overwrite=overwrite,
        )

    def create_skill_from_pattern(
        self,
        pattern_name: str,
        summary: str,
        examples: list[str],
        workflow_steps: list[str],
        constraints: list[str] | None = None,
        created_by: str = "auto-improve",
        overwrite: bool = False,
    ) -> Path:
        constraints = constraints or [
            "Keep the workflow deterministic.",
            "Preserve existing repository contracts and naming conventions.",
        ]
        return self.create_skill(
            name=pattern_name,
            purpose=summary,
            when_to_use=[
                f"Use when this recurring pattern appears: {pattern_name}",
                "Use when task history shows the same workflow at least twice.",
            ],
            inputs=[
                "task_description",
                "historical examples",
                "current repository context",
            ],
            workflow_steps=workflow_steps,
            constraints=constraints,
            examples=examples,
            created_by=created_by,
            overwrite=overwrite,
        )

    def _workflow_from_keywords(self, task_description: str) -> list[str]:
        lowered = task_description.lower()
        if "widget" in lowered:
            return [
                "Inspect the live widget file in widget/ and the mirrored copy in frontend/public/widget/.",
                "Verify the backend widget API contract before changing any payload or config field.",
                "Implement the change in the production widget path first, then mirror it exactly.",
                "Verify embed pages and business-page loading assumptions still hold.",
            ]
        if "schema" in lowered or "migration" in lowered or "database" in lowered:
            return [
                "Inspect the active router and service queries that touch the affected data model.",
                "Confirm live column names against migrations/ before editing code.",
                "Apply the change without reviving deprecated schema fields.",
                "Add or require a migration if the task changes persisted schema.",
            ]
        if "frontend" in lowered or "dashboard" in lowered or "react" in lowered:
            return [
                "Identify the active production route and source component in frontend/src/.",
                "Implement the change in source files, not dist output.",
                "Verify corresponding API usage and route assumptions.",
                "Run the relevant build or smoke-check command.",
            ]
        if "backend" in lowered or "fastapi" in lowered or "api" in lowered:
            return [
                "Inspect the active router, service helper, and direct data-access queries.",
                "Verify auth, schema, and error-handling expectations before changing behavior.",
                "Implement the smallest reusable change that satisfies the task.",
                "Run a targeted validation or compile check.",
            ]
        return [
            "Inspect the active source files and constraints for the task.",
            "Identify any existing repository or generated skill that partially matches.",
            "Implement the change in the primary source of truth, not a legacy copy.",
            "Validate the result with the narrowest reliable verification step.",
        ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create generated skills for AgentNexLiFy.")
    parser.add_argument("task_description", help="Task description or recurring pattern.")
    parser.add_argument("--name", help="Explicit skill name.")
    parser.add_argument("--purpose", help="Explicit skill purpose.")
    parser.add_argument("--created-by", default="codex", help="Creator label.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing generated skill.")
    args = parser.parse_args()

    creator = SkillCreator()
    if args.name and args.purpose:
        skill_path = creator.create_skill(
            name=args.name,
            purpose=args.purpose,
            when_to_use=[f"Use when working on: {args.task_description}"],
            inputs=["task_description", "repository context"],
            workflow_steps=creator._workflow_from_keywords(args.task_description),
            constraints=[
                "Keep the workflow deterministic.",
                "Preserve repository conventions.",
            ],
            examples=[args.task_description],
            created_by=args.created_by,
            overwrite=args.overwrite,
        )
    else:
        skill_path = creator.create_skill_from_task(
            args.task_description,
            created_by=args.created_by,
            overwrite=args.overwrite,
        )

    print(
        {
            "skill_path": str(skill_path),
            "created_at": utc_now_iso(),
            "schema": str(SKILL_SCHEMA_PATH),
        }
    )


if __name__ == "__main__":
    main()
