"""Regression tests for scripts/check_agent_system.py skill inventory."""

import tempfile
import unittest
from pathlib import Path

from scripts import check_agent_system as agent_system


WINDOWS_PLACEHOLDERS = (
    "accessibility",
    "deploy-to-vercel",
    "frontend-design",
    "nodejs-backend-patterns",
    "nodejs-best-practices",
    "seo",
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class CountSkillsTests(unittest.TestCase):
    def test_count_skills_includes_directories_and_real_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            skills = Path(raw)
            (skills / "schema-guard").mkdir()
            (skills / "missing-target").symlink_to("../../.agents/skills/missing-target")

            self.assertEqual(agent_system.count_skills(skills), 2)

    def test_count_skills_includes_windows_materialized_git_symlink_placeholders(
        self,
    ) -> None:
        """core.symlinks=false checks out mode-120000 as a one-line path file."""
        with tempfile.TemporaryDirectory() as raw:
            skills = Path(raw)
            for name in WINDOWS_PLACEHOLDERS:
                newline = "\r\n" if name == "seo" else "\n"
                _write(skills / name, f"../../.agents/skills/{name}{newline}")

            self.assertEqual(agent_system.count_skills(skills), len(WINDOWS_PLACEHOLDERS))

    def test_count_skills_rejects_arbitrary_regular_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            skills = Path(raw)
            (skills / "schema-guard").mkdir()
            _write(skills / "NOTES.md", "not a skill\n")
            _write(skills / "accessibility", "hello world\n")
            _write(skills / "seo", "../../.agents/skills/accessibility\n")
            _write(skills / "frontend-design", "/abs/.agents/skills/frontend-design\n")
            _write(
                skills / "deploy-to-vercel",
                "../../.agents/skills/deploy-to-vercel\nextra line\n",
            )

            self.assertEqual(agent_system.count_skills(skills), 1)

    def test_count_skills_mixed_posix_and_windows_entries(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            skills = Path(raw)
            (skills / "schema-guard").mkdir()
            (skills / "widget-test").symlink_to("../../.agents/skills/widget-test")
            _write(skills / "accessibility", "../../.agents/skills/accessibility\n")
            _write(skills / "README.md", "ignore me\n")

            self.assertEqual(agent_system.count_skills(skills), 3)

    def test_live_skill_inventory_matches_documented_count(self) -> None:
        """Do not weaken the documented-count invariant: live tree must stay 85."""
        self.assertEqual(agent_system.count_skills(), 85)
        documented = agent_system.documented_count(
            agent_system.read_text(".claude/rules/claude-execution-layers.md"),
            r"(\d+) skills, (\d+) commands, (\d+) hooks, (\d+) agents",
        )
        self.assertEqual(documented, 85)


if __name__ == "__main__":
    unittest.main()
