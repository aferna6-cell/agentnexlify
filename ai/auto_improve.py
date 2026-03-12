import argparse
import ast
import hashlib
import re
from pathlib import Path

from . import GENERATED_SKILLS_DIR, REPO_ROOT, ensure_directory, is_ignored_path, relative_path
from .evaluation_engine import EvaluationEngine
from .pattern_extractor import PatternExtractor
from .skill_registry import SkillRegistry
from .task_memory import TaskMemory

TEXT_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".html", ".md", ".json"}
PROTECTED_FILE_PREFIXES = {".env"}
ENTRYPOINT_MODULES = {
    "backend.main",
    "ai.auto_improve",
    "ai.skill_engine",
    "ai.skill_registry",
    "ai.skill_resolver",
    "ai.skill_creator",
    "ai.skill_search",
    "ai.task_memory",
    "ai.pattern_extractor",
    "ai.evaluation_engine",
}
GENERATED_DOC_MARKER_START = "<!-- ai-auto-improve:start -->"
GENERATED_DOC_MARKER_END = "<!-- ai-auto-improve:end -->"


class AutonomousImprover:
    def __init__(self):
        self.registry = SkillRegistry()
        self.memory = TaskMemory()
        self.extractor = PatternExtractor(memory=self.memory)
        self.evaluator = EvaluationEngine(memory=self.memory, registry=self.registry)

    def run(
        self,
        create_skills: bool = False,
        write_report: str | None = None,
        refresh_docs: bool = False,
        task_description: str = "Scheduled daily autonomous improvement run",
    ) -> dict:
        registry = self.registry.rebuild_index()
        patterns = self.extractor.persist_patterns(min_occurrences=2)
        generated_skills = []
        if create_skills:
            generated_skills = self.extractor.generate_skills_from_patterns(
                min_occurrences=2
            )

        report_files = []
        if write_report:
            report_files.append(relative_path((REPO_ROOT / write_report).resolve()))
        if refresh_docs:
            report_files.append("docs/ai-development.md")

        self.evaluator.evaluate_task(
            task_description=task_description,
            skills_used=[],
            files_modified=report_files,
            errors_encountered=[],
            fixes_applied=[
                "updated skill registry",
                "analyzed task memory",
                "generated autonomous improvement report",
            ],
            outcome="success",
            generated_skills=generated_skills,
        )

        summary = {
            "registry": {
                "skill_count": len(registry.get("skills", [])),
                "repository_skills": len(
                    [item for item in registry.get("skills", []) if item.get("source") == "repository"]
                ),
                "generated_skills": len(
                    [item for item in registry.get("skills", []) if item.get("source") == "generated"]
                ),
            },
            "memory": self.memory.summary(),
            "patterns": patterns,
            "generated_skills": generated_skills,
            "duplicates": self.detect_duplicate_code_patterns(),
            "schema_mismatch_risks": self.detect_schema_mismatch_risks(),
            "deprecated_code_patterns": self.detect_deprecated_code_patterns(),
            "unused_modules": self.detect_unused_python_modules(),
            "naming_inconsistencies": self.detect_naming_inconsistencies(),
            "outdated_skills": self.detect_outdated_skills(),
            "skill_description_improvements": self.improve_skill_descriptions(),
            "safety_rules": [
                "Never modify .env files or production credentials.",
                "Never change database schema without a migration file.",
                "Limit autonomous edits to docs, registry files, generated skills, and reports unless a human explicitly expands scope.",
            ],
        }

        report_markdown = self.render_report(summary)
        if write_report:
            report_path = (REPO_ROOT / write_report).resolve()
            self._assert_safe_write(report_path)
            ensure_directory(report_path.parent)
            report_path.write_text(report_markdown, encoding="utf-8")

        if refresh_docs:
            docs_path = REPO_ROOT / "docs" / "ai-development.md"
            self._refresh_docs_summary(docs_path, summary)

        return summary

    def iter_repo_files(self, suffixes: set[str] | None = None):
        for path in REPO_ROOT.rglob("*"):
            if not path.is_file():
                continue
            if is_ignored_path(path):
                continue
            if suffixes and path.suffix.lower() not in suffixes:
                continue
            yield path

    def detect_duplicate_code_patterns(self) -> list[dict]:
        hashes = {}
        duplicates = []
        for path in self.iter_repo_files(TEXT_SUFFIXES):
            if relative_path(path).startswith("ai/memory/"):
                continue
            if path.stat().st_size == 0:
                continue
            digest = hashlib.sha1(path.read_bytes()).hexdigest()
            hashes.setdefault(digest, []).append(relative_path(path))

        for digest, paths in hashes.items():
            if len(paths) > 1:
                duplicates.append(
                    {
                        "hash": digest,
                        "paths": sorted(paths),
                        "suggestion": "Review whether these exact duplicates should share a single source of truth.",
                    }
                )
        duplicates.sort(key=lambda item: len(item["paths"]), reverse=True)
        return duplicates[:10]

    def detect_schema_mismatch_risks(self) -> list[dict]:
        risks = []
        active_source_roots = [
            REPO_ROOT / "backend",
            REPO_ROOT / "frontend" / "src",
            REPO_ROOT / "widget",
        ]
        for root in active_source_roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if is_ignored_path(path):
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                rel = relative_path(path)

                if re.search(
                    r'table\("leads"\)[\s\S]{0,500}?(eq|match|insert|update)\([^)]*tenant_id',
                    text,
                ):
                    risks.append(
                        {
                            "path": rel,
                            "risk": "leads table may be queried with tenant_id instead of client_id",
                        }
                    )
                if re.search(r"\blead_stage\b", text):
                    risks.append(
                        {"path": rel, "risk": "legacy lead_stage naming is present in active code"}
                    )
                if re.search(r"\b(foundation|operations)\b", text):
                    risks.append(
                        {"path": rel, "risk": "legacy plan names appear in active code"}
                    )
                if rel.startswith("backend/routers/") and re.search(
                    r"^from __future__ import annotations\s*$",
                    text,
                    flags=re.MULTILINE,
                ):
                    risks.append(
                        {
                            "path": rel,
                            "risk": "FastAPI router contains from __future__ import annotations",
                        }
                    )

        if (
            (REPO_ROOT / "widget" / "agentnexlify-widget.js").exists()
            and (REPO_ROOT / "public" / "widget.js").exists()
        ):
            risks.append(
                {
                    "path": "widget/, public/",
                    "risk": "multiple widget generations remain in the repository",
                }
            )

        return risks

    def detect_deprecated_code_patterns(self) -> list[dict]:
        findings = []
        if (REPO_ROOT / "landing-page-v2").exists():
            findings.append(
                {
                    "path": "landing-page-v2/",
                    "reason": "legacy static marketing pages still exist beside the React frontend",
                }
            )
        if (REPO_ROOT / "public" / "widget.js").exists():
            findings.append(
                {
                    "path": "public/widget.js",
                    "reason": "older standalone widget artifact still exists beside the production widget",
                }
            )
        if (REPO_ROOT / "_archive").exists():
            findings.append(
                {
                    "path": "_archive/",
                    "reason": "archived backend and scripts remain available and may be mistaken for active code",
                }
            )
        return findings

    def detect_unused_python_modules(self) -> list[dict]:
        modules = {}
        references = {}
        for path in self.iter_repo_files({".py"}):
            rel = relative_path(path)
            if rel.startswith("frontend/") or rel.startswith("demo-platform/"):
                continue
            module_name = rel[:-3].replace("/", ".")
            if module_name.endswith(".__init__"):
                continue
            modules[module_name] = rel
            references[module_name] = 0

        for path in self.iter_repo_files({".py"}):
            rel = relative_path(path)
            module_name = rel[:-3].replace("/", ".")
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported = alias.name
                        for known_module in modules:
                            if imported == known_module or imported.startswith(known_module + "."):
                                references[known_module] += 1
                elif isinstance(node, ast.ImportFrom):
                    base = node.module or ""
                    for alias in node.names:
                        candidate = f"{base}.{alias.name}".strip(".")
                        for known_module in modules:
                            if candidate == known_module or base == known_module:
                                references[known_module] += 1

        findings = []
        for module_name, count in references.items():
            if count == 0 and module_name not in ENTRYPOINT_MODULES:
                findings.append(
                    {
                        "module": module_name,
                        "path": modules[module_name],
                        "reason": "no import references found in repository scan",
                    }
                )
        findings.sort(key=lambda item: item["module"])
        return findings[:20]

    def detect_naming_inconsistencies(self) -> list[dict]:
        findings = []
        if (REPO_ROOT / "backend").exists():
            for path in (REPO_ROOT / "backend").rglob("*.py"):
                if is_ignored_path(path):
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                rel = relative_path(path)
                if "tenant_id" in text and "client_id" in text:
                    findings.append(
                        {
                            "path": rel,
                            "issue": "file mixes tenant_id and client_id naming",
                        }
                    )
        return findings

    def detect_outdated_skills(self) -> list[dict]:
        findings = []
        for skill in self.registry.list_skills():
            skill_path = REPO_ROOT / skill["path"]
            text = skill_path.read_text(encoding="utf-8", errors="ignore")
            if skill.get("source") == "generated":
                required_sections = [
                    "## Purpose",
                    "## When To Use",
                    "## Inputs",
                    "## Workflow Steps",
                    "## Constraints",
                    "## Examples",
                ]
                missing = [section for section in required_sections if section not in text]
                if missing:
                    findings.append(
                        {
                            "skill_name": skill["skill_name"],
                            "path": skill["path"],
                            "issue": f"missing sections: {', '.join(missing)}",
                        }
                    )
            if not skill.get("description"):
                findings.append(
                    {
                        "skill_name": skill["skill_name"],
                        "path": skill["path"],
                        "issue": "skill description is empty",
                    }
                )
        return findings

    def improve_skill_descriptions(self) -> list[dict]:
        suggestions = []
        for skill in self.registry.list_skills():
            description = (skill.get("description") or "").strip()
            if len(description) < 24:
                suggestions.append(
                    {
                        "skill_name": skill["skill_name"],
                        "path": skill["path"],
                        "suggestion": "expand the description so skill resolution has more signal",
                    }
                )
        return suggestions

    def render_report(self, summary: dict) -> str:
        lines = [
            "# AI Auto Improve Report",
            "",
            "## Registry",
            f"- Total skills: {summary['registry']['skill_count']}",
            f"- Repository skills: {summary['registry']['repository_skills']}",
            f"- Generated skills: {summary['registry']['generated_skills']}",
            "",
            "## Memory",
            f"- Tasks recorded: {summary['memory']['tasks_recorded']}",
            f"- Bug patterns: {summary['memory']['bug_patterns']}",
            f"- Architecture patterns: {summary['memory']['architecture_patterns']}",
            f"- Refactor patterns: {summary['memory']['refactor_patterns']}",
            "",
            "## Generated Skills",
        ]

        if summary["generated_skills"]:
            lines.extend(f"- {path}" for path in summary["generated_skills"])
        else:
            lines.append("- No new skills generated in this run.")

        lines.extend(
            [
                "",
                "## Schema Mismatch Risks",
            ]
        )
        if summary["schema_mismatch_risks"]:
            lines.extend(
                f"- `{item['path']}`: {item['risk']}"
                for item in summary["schema_mismatch_risks"]
            )
        else:
            lines.append("- No schema mismatch risks detected in the current scan.")

        lines.extend(
            [
                "",
                "## Duplicate Code Patterns",
            ]
        )
        if summary["duplicates"]:
            for item in summary["duplicates"]:
                lines.append(
                    f"- {', '.join(item['paths'])}: {item['suggestion']}"
                )
        else:
            lines.append("- No exact duplicate text files detected.")

        lines.extend(
            [
                "",
                "## Deprecated Or Legacy Surfaces",
            ]
        )
        if summary["deprecated_code_patterns"]:
            lines.extend(
                f"- `{item['path']}`: {item['reason']}"
                for item in summary["deprecated_code_patterns"]
            )
        else:
            lines.append("- No deprecated code surfaces detected.")

        return "\n".join(lines) + "\n"

    def _refresh_docs_summary(self, docs_path: Path, summary: dict) -> None:
        self._assert_safe_write(docs_path)
        if not docs_path.exists():
            return
        text = docs_path.read_text(encoding="utf-8")
        replacement = (
            f"{GENERATED_DOC_MARKER_START}\n"
            f"Last auto-improve scan found {len(summary['schema_mismatch_risks'])} schema risks, "
            f"{len(summary['duplicates'])} duplicate-code groups, and "
            f"{len(summary['generated_skills'])} newly generated skills.\n"
            f"{GENERATED_DOC_MARKER_END}"
        )
        pattern = re.compile(
            rf"{re.escape(GENERATED_DOC_MARKER_START)}.*?{re.escape(GENERATED_DOC_MARKER_END)}",
            flags=re.DOTALL,
        )
        if pattern.search(text):
            updated = pattern.sub(replacement, text)
        else:
            updated = text.rstrip() + "\n\n" + replacement + "\n"
        docs_path.write_text(updated, encoding="utf-8")

    def _assert_safe_write(self, path: Path) -> None:
        if path.name.startswith(tuple(PROTECTED_FILE_PREFIXES)):
            raise ValueError(f"Refusing to write protected file: {path}")
        if GENERATED_SKILLS_DIR not in path.parents and path != GENERATED_SKILLS_DIR:
            allowed_roots = {
                REPO_ROOT / "docs",
                REPO_ROOT / "skills",
                REPO_ROOT / "ai",
                REPO_ROOT / ".github",
            }
            if not any(root == path or root in path.parents for root in allowed_roots):
                raise ValueError(f"Refusing to write outside autonomous-system roots: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the autonomous repository improvement loop.")
    parser.add_argument("--create-skills", action="store_true")
    parser.add_argument("--write-report", help="Write a Markdown report relative to the repo root.")
    parser.add_argument("--refresh-docs", action="store_true")
    parser.add_argument(
        "--task-description",
        default="Scheduled daily autonomous improvement run",
    )
    args = parser.parse_args()

    improver = AutonomousImprover()
    print(
        improver.run(
            create_skills=args.create_skills,
            write_report=args.write_report,
            refresh_docs=args.refresh_docs,
            task_description=args.task_description,
        )
    )


if __name__ == "__main__":
    main()
