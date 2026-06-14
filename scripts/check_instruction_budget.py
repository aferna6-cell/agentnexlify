"""Keep always-on agent instructions small and intentional.

This guardrail catches the failure mode where one-off prompt fixes get added to
UserPromptSubmit and silently tax every future Claude Code turn.
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT / ".claude" / "settings.json"
CLAUDE_MD_PATH = ROOT / "CLAUDE.md"

MAX_CLAUDE_MD_LINES = 200
MAX_USER_PROMPT_HOOKS = 6
MAX_LITERAL_ECHO_HOOKS = 0


def check(condition: bool, label: str, failures: list[str]) -> None:
    if condition:
        print(f"PASS {label}")
        return
    print(f"FAIL {label}")
    failures.append(label)


def user_prompt_hooks(settings: dict) -> list[dict]:
    hooks: list[dict] = []
    for block in settings.get("hooks", {}).get("UserPromptSubmit", []):
        hooks.extend(block.get("hooks", []))
    return hooks


def main() -> int:
    failures: list[str] = []
    settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    claude_lines = CLAUDE_MD_PATH.read_text(encoding="utf-8").splitlines()

    hooks = user_prompt_hooks(settings)
    literal_echo_hooks = [
        hook
        for hook in hooks
        if hook.get("type") == "command"
        and str(hook.get("command", "")).strip().startswith("echo ")
    ]
    hook_text = "\n".join(str(hook.get("command", "")) for hook in hooks)

    check(
        len(claude_lines) <= MAX_CLAUDE_MD_LINES,
        f"CLAUDE.md stays at or below {MAX_CLAUDE_MD_LINES} lines ({len(claude_lines)})",
        failures,
    )
    check(
        len(hooks) <= MAX_USER_PROMPT_HOOKS,
        f"UserPromptSubmit hook count stays at or below {MAX_USER_PROMPT_HOOKS} ({len(hooks)})",
        failures,
    )
    check(
        len(literal_echo_hooks) <= MAX_LITERAL_ECHO_HOOKS,
        "UserPromptSubmit avoids unconditional literal echo prompt injections",
        failures,
    )
    for stale_phrase in (
        "CAVEMAN MODE ACTIVE",
        "12 CLAUDE USAGE PATTERNS",
        "MODEL ROUTING",
        "PARALLEL APPROACHES",
        "PROMPT LIBRARY",
    ):
        check(stale_phrase not in hook_text, f"UserPromptSubmit does not inject {stale_phrase}", failures)

    if failures:
        print("")
        print(f"{len(failures)} instruction-budget check(s) failed.")
        return 1

    print("")
    print("Instruction budget check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
