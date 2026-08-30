import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".ai" / "slack-agent-team.json"


class SlackAgentTeamTests(unittest.TestCase):
    def test_config_names_live_hq_and_specialists(self):
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        existing = {row["name"]: row["id"] for row in config["existing_channels"]}
        self.assertEqual(existing["agent-nexlify"], "C0BTKCYP8TG")
        self.assertEqual(
            [row["name"] for row in config["specialist_channels"]],
            ["agent-grok", "agent-product", "agent-code", "agent-review"],
        )
        self.assertEqual(config["durable_hub"], "github_issue")

    def test_each_agent_prompt_exists_and_blocks_wrong_repo(self):
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        for agent in config["agents"]:
            prompt = ROOT / agent["prompt_file"]
            text = prompt.read_text(encoding="utf-8")
            self.assertIn("Never use `Agent-Nexlify-OS`", text)
            self.assertIn("teamctl", text)
            self.assertIn("[skip ci]", text)

    def test_check_script_passes(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_slack_agent_team.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
