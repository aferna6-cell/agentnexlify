"""CLI runner for the GitHub issue autopilot classifier and dispatcher.

Polls open issues labeled `ai-ready`, classifies each issue with Claude Haiku,
and dispatches at most one ready issue to Codex in a fresh git worktree.

Usage:
    python scripts/autopilot/classify_and_dispatch.py
    python scripts/autopilot/classify_and_dispatch.py --dry-run
    python scripts/autopilot/classify_and_dispatch.py --dry-run --issue 1

Exit codes:
    0 - classification or dispatch completed
    1 - hard failure
    2 - no eligible work found
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.autopilot import labels, state_marker  # noqa: E402

CLASSIFIER_MODEL = "claude-haiku-4-5-20251001"
DISPATCHER_MODEL = "claude-sonnet-4-6"
AUTOPILOT_AUTHOR_NAME = "Autopilot Bot"
AUTOPILOT_AUTHOR_EMAIL = "autopilot-bot@users.noreply.github.com"
WORKFLOW_CONTRACT_PATH = "docs/AUTOPILOT_WORKFLOW.md"
DEFAULT_MAX_ACTIVE_RUNS = 1

CLASSIFIER_SYSTEM = (
    "Classify this GitHub issue as READY, NEEDS_INFO, or OUT_OF_SCOPE. "
    "READY means implementation requirements are clear enough for a Sonnet "
    "executor to complete autonomously. NEEDS_INFO means the issue is missing "
    "acceptance criteria, reproduction steps, or affected file paths. "
    "OUT_OF_SCOPE means the issue requires human judgment (security, billing, "
    "customer communications, legal). Respond JSON-only: "
    '{"classification":"READY|NEEDS_INFO|OUT_OF_SCOPE","reason":"...",'
    '"needed_info":"...","proposed_plan":"..."}'
)


class AutopilotError(Exception):
    """Raised when the autopilot cannot safely continue."""


@dataclass(frozen=True)
class ClassificationResult:
    """Classifier output normalized for dispatch decisions."""

    classification: str
    reason: str
    needed_info: str | None = None
    proposed_plan: str | None = None
    raw_reply: str | None = None
    malformed: bool = False


@dataclass(frozen=True)
class ProofOfWork:
    """Human-review packet attached to autopilot pull requests."""

    changed_files: str
    local_check: str
    residual_risks: str


class TokenBudget:
    """Simple per-run Anthropic SDK token usage guard."""

    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens
        self.used_tokens = 0

    def add_response_usage(self, response: Any) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        total = 0
        for attr in (
            "input_tokens",
            "output_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
        ):
            total += int(getattr(usage, attr, 0) or 0)
        self.used_tokens += total
        if self.used_tokens > self.max_tokens:
            raise AutopilotError(
                f"token budget exceeded: {self.used_tokens} > {self.max_tokens}"
            )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Classify issues but skip label transitions, dispatch, and comments.",
    )
    parser.add_argument(
        "--issue",
        type=int,
        default=None,
        help="Classify a single issue number instead of the ai-ready queue.",
    )
    return parser


def _token_budget_from_env() -> TokenBudget:
    raw_limit = os.environ.get("AUTOPILOT_MAX_TOKENS_PER_RUN", "200000")
    try:
        max_tokens = int(raw_limit)
    except ValueError as exc:
        raise AutopilotError("autopilot token budget must be an integer") from exc
    return TokenBudget(max_tokens=max_tokens)


def _max_active_runs_from_env() -> int:
    raw_limit = os.environ.get("AUTOPILOT_MAX_ACTIVE_RUNS", str(DEFAULT_MAX_ACTIVE_RUNS))
    try:
        limit = int(raw_limit)
    except ValueError as exc:
        raise AutopilotError("autopilot active-run cap must be an integer") from exc
    if limit < 1:
        raise AutopilotError("autopilot active-run cap must be at least 1")
    return limit


def _workflow_contract(max_chars: int = 6000) -> str:
    path = _REPO_ROOT / WORKFLOW_CONTRACT_PATH
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return f"{WORKFLOW_CONTRACT_PATH} was not readable. Follow repo autopilot defaults."
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n[workflow contract truncated]"


def _tail(text: str, max_chars: int = 2000) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _run(
    args: list[str],
    *,
    cwd: Path = _REPO_ROOT,
    input_text: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args,
        cwd=str(cwd),
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and completed.returncode != 0:
        raise AutopilotError(
            "command failed "
            f"({args[0]} exit {completed.returncode})\n"
            f"stdout:\n{_tail(completed.stdout)}\n"
            f"stderr:\n{_tail(completed.stderr)}"
        )
    return completed


def _gh_json(args: list[str]) -> Any:
    completed = _run(["gh", *args])
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AutopilotError(f"gh returned invalid JSON for {' '.join(args)}") from exc


def _require_cli(name: str) -> None:
    if shutil.which(name) is None:
        raise AutopilotError(
            f"required CLI `{name}` was not found on PATH; dispatch aborted"
        )


def _fetch_issue(issue_number: int) -> dict[str, Any]:
    return _gh_json(
        [
            "issue",
            "view",
            str(issue_number),
            "--json",
            "number,title,body,labels,comments",
        ]
    )


def _candidate_issues(issue_number: int | None = None) -> list[dict[str, Any]]:
    if issue_number is not None:
        return [_fetch_issue(issue_number)]

    raw_issues = _gh_json(
        [
            "issue",
            "list",
            "--label",
            labels.AI_READY,
            "--state",
            "open",
            "--limit",
            "50",
            "--json",
            "number,title,body,labels,comments",
        ]
    )
    return [_fetch_issue(int(issue["number"])) for issue in raw_issues]


def _active_autopilot_issue_count() -> int:
    active = _gh_json(
        [
            "issue",
            "list",
            "--label",
            labels.WIP_AUTOPILOT,
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number",
        ]
    )
    return len(active)


def _issue_label_names(issue: dict[str, Any]) -> set[str]:
    return labels.normalize_label_names(issue.get("labels") or [])


def _anthropic_text(response: Any) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(str(text))
    return "\n".join(parts).strip()


def _classification_payload(issue: dict[str, Any]) -> str:
    comments = []
    for comment in issue.get("comments") or []:
        if state_marker.parse_state_markers(comment.get("body") if isinstance(comment, dict) else ""):
            continue
        comments.append(comment)
    payload = {
        "number": issue.get("number"),
        "title": issue.get("title"),
        "body": issue.get("body"),
        "comments": comments,
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def classify_issue(
    issue: dict[str, Any],
    *,
    budget: TokenBudget,
    logger: logging.Logger,
) -> ClassificationResult:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise AutopilotError("Anthropic API key is not configured for this runner")

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=CLASSIFIER_MODEL,
        max_tokens=1200,
        system=CLASSIFIER_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    "Classify this GitHub issue for the AgentNexLiFy autopilot.\n\n"
                    f"Workflow contract:\n```markdown\n{_workflow_contract()}\n```\n\n"
                    f"{_classification_payload(issue)}"
                ),
            }
        ],
    )
    budget.add_response_usage(response)
    raw_reply = _anthropic_text(response)
    logger.info(
        "classifier used %d/%d Anthropic SDK tokens",
        budget.used_tokens,
        budget.max_tokens,
    )

    try:
        parsed = json.loads(raw_reply)
        decision = str(parsed.get("classification") or "").upper()
        if decision not in {
            labels.READY,
            labels.NEEDS_INFO_DECISION,
            labels.OUT_OF_SCOPE,
        }:
            raise ValueError(f"unsupported classification {decision!r}")
        return ClassificationResult(
            classification=decision,
            reason=str(parsed.get("reason") or "").strip(),
            needed_info=(
                str(parsed.get("needed_info")).strip()
                if parsed.get("needed_info") is not None
                else None
            ),
            proposed_plan=(
                str(parsed.get("proposed_plan")).strip()
                if parsed.get("proposed_plan") is not None
                else None
            ),
            raw_reply=raw_reply,
        )
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return ClassificationResult(
            classification=labels.NEEDS_INFO_DECISION,
            reason=f"Classifier returned malformed JSON: {exc}",
            needed_info=(
                "Classifier returned a malformed reply. Human review is required "
                "before dispatch.\n\nRaw classifier reply:\n\n"
                f"```text\n{raw_reply[:4000]}\n```"
            ),
            raw_reply=raw_reply,
            malformed=True,
        )


def _apply_label_transition(
    issue_number: int,
    transition: labels.LabelTransition,
    *,
    current_labels: set[str],
) -> None:
    for label in transition.add:
        if label not in current_labels:
            _run(["gh", "issue", "edit", str(issue_number), "--add-label", label])
            current_labels.add(label)
    for label in transition.remove:
        if label in current_labels:
            _run(["gh", "issue", "edit", str(issue_number), "--remove-label", label])
            current_labels.discard(label)


def _post_issue_comment(issue_number: int, body: str) -> None:
    _run(["gh", "issue", "comment", str(issue_number), "--body", body])


def _slugify(value: str, max_length: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug or "issue")[:max_length].strip("-") or "issue"


def _format_dispatch_prompt(
    issue: dict[str, Any],
    result: ClassificationResult,
) -> str:
    plan = result.proposed_plan or "Use the issue body as the implementation plan."
    return f"""\
You are Codex running the AgentNexLiFy issue autopilot executor.

Model routing target: {DISPATCHER_MODEL}.

Issue #{issue["number"]}: {issue.get("title") or ""}

Classifier reason:
{result.reason}

Proposed plan:
{plan}

Issue body:
{issue.get("body") or ""}

Workflow contract:
```markdown
{_workflow_contract()}
```

Requirements:
- Implement the issue directly in this worktree.
- Keep the change scoped to the issue and the proposed plan.
- Do not commit, push, create labels, or open a pull request.
- Do not hardcode secrets.
- Do not add future-annotations imports.
- Prefer existing repo patterns and smallest concrete changes.
- Leave the worktree ready for `bash scripts/hooks/pre-commit`.
"""


def _write_prompt_file(worktree: Path, issue_number: int, prompt: str) -> Path:
    prompt_dir = worktree / ".autopilot-prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"issue-{issue_number}.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path


def _run_codex(prompt_path: Path, *, cwd: Path) -> None:
    _require_cli("codex")
    prompt_text = prompt_path.read_text(encoding="utf-8")
    _run(["codex", "exec", "--write", prompt_text], cwd=cwd)


def _run_pre_commit_gate(worktree: Path) -> None:
    _run(["git", "add", "-A"], cwd=worktree)
    _run(["bash", "scripts/hooks/pre-commit"], cwd=worktree)


def _changed_files_summary(worktree: Path) -> str:
    staged = _run(
        ["git", "diff", "--cached", "--name-status"],
        cwd=worktree,
    ).stdout.strip()
    if staged:
        return staged
    return _run(["git", "status", "--short"], cwd=worktree).stdout.strip() or "No files listed"


def _proof_of_work(worktree: Path) -> ProofOfWork:
    return ProofOfWork(
        changed_files=_changed_files_summary(worktree),
        local_check="bash scripts/hooks/pre-commit: passed",
        residual_risks=(
            "GitHub CI and human review still required. Visual review is required "
            "for UI-facing changes unless screenshots are attached separately."
        ),
    )


def _format_pr_body(
    issue: dict[str, Any],
    result: ClassificationResult,
    proof: ProofOfWork,
) -> str:
    issue_number = int(issue["number"])
    plan = result.proposed_plan or result.reason or "Autopilot implementation."
    return f"""\
Closes #{issue_number}

## Autopilot Proof Of Work

Workflow contract: `{WORKFLOW_CONTRACT_PATH}`

Classifier reason:
{result.reason or "No classifier reason returned."}

Proposed plan:
{plan}

Changed files:
```text
{proof.changed_files}
```

Local verification:
{proof.local_check}

Residual risks:
{proof.residual_risks}

Human review required before merge.
"""


def _configure_git_author(worktree: Path) -> None:
    _run(["git", "config", "user.name", AUTOPILOT_AUTHOR_NAME], cwd=worktree)
    _run(["git", "config", "user.email", AUTOPILOT_AUTHOR_EMAIL], cwd=worktree)


def _cleanup_worktree(worktree: Path, logger: logging.Logger) -> None:
    if not worktree.exists():
        return
    completed = _run(
        ["git", "worktree", "remove", "--force", str(worktree)],
        check=False,
    )
    if completed.returncode != 0:
        logger.warning("failed to remove worktree %s: %s", worktree, completed.stderr)


def dispatch_issue(
    issue: dict[str, Any],
    result: ClassificationResult,
    *,
    logger: logging.Logger,
) -> None:
    _require_cli("codex")
    issue_number = int(issue["number"])
    slug = _slugify(str(issue.get("title") or "issue"))
    branch = f"autopilot/issue-{issue_number}-{slug}"
    worktree = _REPO_ROOT.parent / f"agentnexlify-autopilot-{issue_number}"

    if worktree.exists():
        raise AutopilotError(f"stale autopilot worktree already exists: {worktree}")

    try:
        _run(["git", "worktree", "add", str(worktree), "-b", branch])
        prompt_path = _write_prompt_file(
            worktree,
            issue_number,
            _format_dispatch_prompt(issue, result),
        )
        logger.info("dispatching issue %s to Codex prompt %s", issue_number, prompt_path)
        _run_codex(prompt_path, cwd=worktree)

        status = _run(["git", "status", "--porcelain"], cwd=worktree).stdout.strip()
        if not status:
            raise AutopilotError("Codex completed without producing file changes")

        _configure_git_author(worktree)
        _run_pre_commit_gate(worktree)
        proof = _proof_of_work(worktree)
        _run(
            [
                "git",
                "commit",
                "-m",
                f"autopilot: implement issue #{issue_number}",
            ],
            cwd=worktree,
        )
        _run(["git", "push", "--set-upstream", "origin", branch], cwd=worktree)

        _run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                f"autopilot: {issue.get('title') or f'issue #{issue_number}'}",
                "--body",
                _format_pr_body(issue, result, proof),
                "--label",
                labels.AUTOPILOT_PR,
                "--base",
                "main",
                "--head",
                branch,
            ],
            cwd=worktree,
        )
    finally:
        _cleanup_worktree(worktree, logger)


def _handle_needs_info(
    issue: dict[str, Any],
    result: ClassificationResult,
    issue_hash: str,
) -> None:
    issue_number = int(issue["number"])
    info = result.needed_info or "Please add acceptance criteria or affected file paths."
    body = (
        "Autopilot needs more information before dispatching this issue.\n\n"
        f"{info}\n\n"
        f"Reason: {result.reason or 'No classifier reason returned.'}\n\n"
        f"{state_marker.make_state_marker(issue_hash)}"
    )
    _post_issue_comment(issue_number, body)
    current = _issue_label_names(issue)
    _apply_label_transition(
        issue_number,
        labels.transition_for(labels.NEEDS_INFO_DECISION, current),
        current_labels=current,
    )


def _handle_out_of_scope(
    issue: dict[str, Any],
    result: ClassificationResult,
    issue_hash: str,
) -> None:
    issue_number = int(issue["number"])
    body = (
        "Autopilot skipped this issue because it requires human judgment.\n\n"
        f"Reason: {result.reason or 'No classifier reason returned.'}\n\n"
        f"{state_marker.make_state_marker(issue_hash)}"
    )
    _post_issue_comment(issue_number, body)
    current = _issue_label_names(issue)
    _apply_label_transition(
        issue_number,
        labels.transition_for(labels.OUT_OF_SCOPE, current),
        current_labels=current,
    )


def _handle_dispatch_failure(issue: dict[str, Any], message: str) -> None:
    issue_number = int(issue["number"])
    body = (
        "Autopilot dispatch failed. Human intervention is required.\n\n"
        f"```text\n{_tail(message, 6000)}\n```"
    )
    _post_issue_comment(issue_number, body)
    current = _issue_label_names(_fetch_issue(issue_number))
    _apply_label_transition(
        issue_number,
        labels.transition_for(labels.DISPATCH_FAILED, current),
        current_labels=current,
    )


def _should_skip_issue(issue: dict[str, Any], logger: logging.Logger) -> bool:
    issue_number = int(issue["number"])
    current = _issue_label_names(issue)
    issue_hash = state_marker.compute_state_hash(issue)
    latest_hash = state_marker.latest_state_hash(issue.get("comments") or [])

    if labels.WIP_AUTOPILOT in current:
        logger.info("issue %s skipped: already wip-autopilot", issue_number)
        return True
    if labels.AUTOPILOT_SKIPPED in current:
        logger.info("issue %s skipped: already autopilot-skipped", issue_number)
        return True
    if labels.AUTOPILOT_FAILED in current:
        logger.info("issue %s skipped: already autopilot-failed", issue_number)
        return True
    if labels.NEEDS_INFO in current and latest_hash == issue_hash:
        logger.info("issue %s skipped: needs-info state unchanged", issue_number)
        return True
    return False


def run(args: argparse.Namespace, logger: logging.Logger) -> int:
    budget = _token_budget_from_env()
    if not args.dry_run:
        active_count = _active_autopilot_issue_count()
        max_active = _max_active_runs_from_env()
        if active_count >= max_active:
            logger.info(
                "autopilot active-run cap reached: %d/%d wip issues",
                active_count,
                max_active,
            )
            return 2

    issues = _candidate_issues(args.issue)
    if not issues:
        logger.info("no open ai-ready issues found")
        return 2

    dispatched = False
    did_work = False

    for issue in issues:
        issue_number = int(issue["number"])
        if _should_skip_issue(issue, logger):
            continue

        issue_hash = state_marker.compute_state_hash(issue)
        result = classify_issue(issue, budget=budget, logger=logger)
        did_work = True
        logger.info(
            "issue %s classified as %s: %s",
            issue_number,
            result.classification,
            result.reason,
        )

        if args.dry_run:
            continue

        if result.classification == labels.NEEDS_INFO_DECISION:
            _handle_needs_info(issue, result, issue_hash)
            continue

        if result.classification == labels.OUT_OF_SCOPE:
            _handle_out_of_scope(issue, result, issue_hash)
            continue

        if result.classification == labels.READY:
            current = _issue_label_names(issue)
            _apply_label_transition(
                issue_number,
                labels.transition_for(labels.READY, current),
                current_labels=current,
            )
            try:
                dispatch_issue(issue, result, logger=logger)
            except AutopilotError as exc:
                _handle_dispatch_failure(issue, str(exc))
                raise
            dispatched = True
            did_work = True
            break

    if dispatched or did_work:
        return 0
    logger.info("no eligible issue required action")
    return 2


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger("autopilot.classify_and_dispatch")
    args = _build_parser().parse_args()
    try:
        return run(args, logger)
    except AutopilotError as exc:
        logger.error("autopilot issue loop failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
