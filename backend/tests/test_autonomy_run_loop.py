"""CLI contract tests for scripts/autonomy/run_loop.py.

The driving Claude Code session talks to this module by argv and reads its
answer off stdout, so the contract is narrow and total:

  1. Exactly ONE JSON object on stdout, always. The session never parses prose —
     including when the driver itself broke, which is why a crash still emits
     ``{"status": "driver_error", ...}`` before exiting 1.
  2. Exit 0 means "the loop advanced correctly", which covers idling, parking
     and escalating. Those are successful dispositions, not errors.
  3. `resume` continues a run started by a *previous* process, which is the
     whole reason state lives in ``--state-dir``.
  4. The global flags work on both sides of the subcommand.
  5. `start` refuses to run at all when preflight reports blockers, and
     ``--skip-preflight`` is a real bypass.

`main(argv)` is called in-process rather than shelled out, so a failure shows a
Python traceback instead of a return code.

Verification seam: the CLI passes no ``runner`` in ``extras``, so `_verify`
would shell out to the real 20-gate `scripts/ci_local.sh`. These tests
monkeypatch ``scripts.autonomy.gates.run_local_ci`` instead — see the note in
the report accompanying this file.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from scripts.autonomy import gates  # noqa: E402
from scripts.autonomy.run_loop import main  # noqa: E402
from scripts.autonomy.runner import GateResult  # noqa: E402

CI_PASS = "RESULT: PASS (20 required gates green)"
CI_FAIL = "  FAIL  migration numbering\nRESULT: FAIL (1 required gate(s) failed)"

IMPLEMENT_RESULT = '{"summary": "added the column", "files_changed": ["backend/x.py"]}'
MERGE_RESULT = json.dumps({"merged": True, "sha": "cafe1234"})
PR_RESULT = '{"pr_url": "https://github.com/o/r/pull/7", "pr_number": 7}'
ESCALATE_RESULT = '{"escalated": true}'


# --------------------------------------------------------------------------
# Harness
# --------------------------------------------------------------------------


def run_cli(capsys, argv):
    """Invoke the CLI and assert its one-JSON-object-on-stdout contract."""
    code = main(argv)
    out = capsys.readouterr().out.strip()

    assert out, "the CLI must always answer on stdout"
    assert out.startswith("{") and out.endswith("}")
    # json.loads rejects two concatenated objects, so this also proves there is
    # exactly one.
    return code, json.loads(out)


def fake_local_ci(passed):
    def _run(compare_ref="origin/main", *, runner=None, timeout=3600):
        return GateResult(
            passed=passed,
            name="local-ci",
            summary=CI_PASS if passed else CI_FAIL,
            duration_seconds=0.01,
            returncode=0 if passed else 1,
        )

    return _run


@pytest.fixture()
def green_ci(monkeypatch):
    monkeypatch.setattr(gates, "run_local_ci", fake_local_ci(True))


@pytest.fixture()
def red_ci(monkeypatch):
    monkeypatch.setattr(gates, "run_local_ci", fake_local_ci(False))


def write_backlog(tmp_path, entries, name="backlog.json"):
    path = tmp_path / name
    path.write_text(json.dumps({"items": entries}))
    return str(path)


def entry(item_id="gh-7", **overrides):
    row = {
        "id": item_id,
        "title": f"Do {item_id}",
        "value": 1.0,
        "effort": 0.2,
        "confidence": 0.9,
        "risk": "low",
        "url": f"https://github.com/o/r/issues/{item_id}",
    }
    row.update(overrides)
    return row


DUD = entry("gh-dud", value=0.1, effort=0.9, confidence=0.5)


@pytest.fixture()
def state_dir(tmp_path):
    return str(tmp_path / "state")


@pytest.fixture()
def backlog(tmp_path):
    return write_backlog(tmp_path, [entry("gh-7")])


def start_argv(state_dir, backlog, *extra):
    return ["start", "--state-dir", state_dir, "--skip-preflight", "--backlog", backlog, *extra]


def resume_argv(state_dir, run_id, result):
    return ["resume", "--state-dir", state_dir, "--run-id", run_id, "--result", result]


# --------------------------------------------------------------------------
# start — the response shape
# --------------------------------------------------------------------------


def test_start_emits_one_json_object_with_the_session_contract(
    capsys, green_ci, state_dir, backlog
):
    code, payload = run_cli(capsys, start_argv(state_dir, backlog))

    assert code == 0
    assert payload["status"] == "awaiting_action"
    assert payload["run_id"]
    assert payload["journal"] == ["selected gh-7 (Do gh-7)"]
    assert isinstance(payload["budget"], dict)
    assert payload["budget"]["node_runs"] >= 1
    assert payload["candidates"] == 1
    assert payload["outcome"] is None


def test_a_paused_start_names_the_action_and_carries_its_payload(
    capsys, green_ci, state_dir, backlog
):
    _, payload = run_cli(capsys, start_argv(state_dir, backlog))

    assert payload["action"] == "implement"
    assert payload["payload"]["task"]["id"] == "gh-7"
    assert payload["payload"]["attempt"] == 1
    assert "instructions" in payload["payload"]


def test_start_writes_its_checkpoint_under_the_requested_state_dir(
    capsys, green_ci, state_dir, backlog
):
    _, payload = run_cli(capsys, start_argv(state_dir, backlog))

    assert os.path.isfile(os.path.join(state_dir, payload["run_id"], "current.json"))


def test_start_honours_an_explicit_run_id(capsys, green_ci, state_dir, backlog):
    _, payload = run_cli(
        capsys, start_argv(state_dir, backlog, "--run-id", "loop-2026-07-27")
    )

    assert payload["run_id"] == "loop-2026-07-27"


# --------------------------------------------------------------------------
# Global flags on both sides of the subcommand
# --------------------------------------------------------------------------


def test_global_flags_parse_after_the_subcommand(capsys, green_ci, state_dir, backlog):
    """`run_loop start --state-dir X` is what anyone actually types."""
    code, payload = run_cli(
        capsys, ["start", "--state-dir", state_dir, "--skip-preflight", "--backlog", backlog]
    )

    assert code == 0
    assert os.path.isdir(os.path.join(state_dir, payload["run_id"]))


def test_global_flags_parse_before_the_subcommand(
    capsys, green_ci, monkeypatch, tmp_path, backlog
):
    """`run_loop --state-dir X start` must reach the same state directory.

    Regression guard: argparse only *matched* a parent-level flag before the
    subcommand, so the fix attached the same flags to every subparser. cwd is
    moved into tmp_path so a regression writes its fallback `.autonomy/` there
    instead of into the repo.
    """
    monkeypatch.chdir(tmp_path)
    state_dir = str(tmp_path / "state")

    code, payload = run_cli(
        capsys, ["--state-dir", state_dir, "start", "--skip-preflight", "--backlog", backlog]
    )

    assert code == 0
    assert os.path.isdir(os.path.join(state_dir, payload["run_id"])), (
        "the run landed outside --state-dir; the pre-subcommand flag was dropped"
    )


def test_prs_opened_today_parses_after_the_subcommand(
    capsys, green_ci, state_dir, backlog
):
    """The quota flag must actually reach `land`, not just parse."""
    code, payload = run_cli(
        capsys,
        start_argv(state_dir, backlog, "--prs-opened-today", "4"),
    )
    _, resumed = run_cli(
        capsys,
        resume_argv(state_dir, payload["run_id"], IMPLEMENT_RESULT)
        + ["--prs-opened-today", "4"],
    )

    assert code == 0
    assert resumed["outcome"] == "parked"


# --------------------------------------------------------------------------
# resume — the cross-process property
# --------------------------------------------------------------------------


def test_resume_advances_a_run_started_in_a_prior_main_call(
    capsys, green_ci, state_dir, backlog
):
    """Two separate `main()` calls share nothing but ``--state-dir``."""
    _, started = run_cli(capsys, start_argv(state_dir, backlog))
    assert started["action"] == "implement"

    code, resumed = run_cli(
        capsys, resume_argv(state_dir, started["run_id"], IMPLEMENT_RESULT)
    )

    assert code == 0
    assert resumed["run_id"] == started["run_id"]
    assert resumed["status"] == "awaiting_action"
    assert resumed["action"] == "open_pr"
    assert resumed["payload"]["implementation"]["summary"] == "added the column"
    assert "verify: PASS" in resumed["journal"]


def test_a_full_run_reaches_merged_across_four_invocations(
    capsys, green_ci, state_dir, backlog
):
    _, started = run_cli(capsys, start_argv(state_dir, backlog))
    _, mid = run_cli(capsys, resume_argv(state_dir, started["run_id"], IMPLEMENT_RESULT))
    _, opened = run_cli(capsys, resume_argv(state_dir, mid["run_id"], PR_RESULT))

    assert opened["action"] == "merge"

    code, final = run_cli(
        capsys,
        resume_argv(state_dir, opened["run_id"], MERGE_RESULT),
    )

    assert code == 0
    assert final["status"] == "completed"
    assert final["outcome"] == "merged"
    assert final["journal"][-1] == "merged https://github.com/o/r/pull/7"


def test_result_can_be_read_from_a_file(
    capsys, green_ci, state_dir, backlog, tmp_path
):
    result_file = tmp_path / "implement.json"
    result_file.write_text(IMPLEMENT_RESULT)

    _, started = run_cli(capsys, start_argv(state_dir, backlog))
    code, resumed = run_cli(
        capsys, resume_argv(state_dir, started["run_id"], f"@{result_file}")
    )

    assert code == 0
    assert resumed["action"] == "open_pr"
    assert resumed["payload"]["implementation"]["files_changed"] == ["backend/x.py"]


def test_resuming_an_unknown_run_is_a_driver_error(capsys, state_dir):
    code, payload = run_cli(
        capsys, resume_argv(state_dir, "no-such-run", IMPLEMENT_RESULT)
    )

    assert code == 1
    assert payload["status"] == "driver_error"
    assert "no checkpoint found" in payload["error"]


# --------------------------------------------------------------------------
# status
# --------------------------------------------------------------------------


def test_status_of_an_unknown_run_id_is_unknown_and_not_an_error(capsys, state_dir):
    code, payload = run_cli(
        capsys, ["status", "--state-dir", state_dir, "--run-id", "never-existed"]
    )

    assert code == 0
    assert payload == {"run_id": "never-existed", "status": "unknown"}


def test_status_inspects_a_paused_run_without_advancing_it(
    capsys, green_ci, state_dir, backlog
):
    _, started = run_cli(capsys, start_argv(state_dir, backlog))

    code, payload = run_cli(
        capsys, ["status", "--state-dir", state_dir, "--run-id", started["run_id"]]
    )

    assert code == 0
    assert payload["status"] == "awaiting_action"
    assert payload["action"] == "implement"
    assert payload["outcome"] is None
    assert payload["journal"] == started["journal"]


# --------------------------------------------------------------------------
# Driver errors always answer in JSON
# --------------------------------------------------------------------------


def test_a_missing_backlog_file_exits_one_but_still_emits_json(capsys, state_dir):
    code, payload = run_cli(
        capsys,
        ["start", "--state-dir", state_dir, "--skip-preflight", "--backlog", "/nope/missing.json"],
    )

    assert code == 1
    assert payload["status"] == "driver_error"
    assert "FileNotFoundError" in payload["error"]


def test_a_malformed_backlog_exits_one_but_still_emits_json(
    capsys, state_dir, tmp_path
):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")

    code, payload = run_cli(capsys, start_argv(state_dir, str(bad)))

    assert code == 1
    assert payload["status"] == "driver_error"
    assert "JSONDecodeError" in payload["error"]


def test_a_backlog_item_without_an_id_exits_one_but_still_emits_json(
    capsys, state_dir, tmp_path
):
    path = write_backlog(tmp_path, [{"title": "no id"}])

    code, payload = run_cli(capsys, start_argv(state_dir, path))

    assert code == 1
    assert payload["status"] == "driver_error"
    assert "needs an id" in payload["error"]


# --------------------------------------------------------------------------
# Successful non-PR dispositions still exit 0
# --------------------------------------------------------------------------


def test_idle_is_a_success_and_exits_zero(capsys, state_dir, tmp_path):
    path = write_backlog(tmp_path, [DUD])

    code, payload = run_cli(capsys, start_argv(state_dir, path))

    assert code == 0
    assert payload["status"] == "completed"
    assert payload["outcome"] == "idle"
    assert "error" not in payload


def test_dry_is_a_success_and_exits_zero(capsys, state_dir, tmp_path):
    path = write_backlog(tmp_path, [DUD])

    code, payload = run_cli(capsys, start_argv(state_dir, path, "--idle-rounds", "1"))

    assert code == 0
    assert payload["outcome"] == "dry"


def test_escalation_is_a_success_and_exits_zero(
    capsys, red_ci, state_dir, backlog
):
    code, payload = run_cli(capsys, start_argv(state_dir, backlog))
    run_id = payload["run_id"]

    for _ in range(3):
        assert payload["action"] == "implement"
        code, payload = run_cli(
            capsys, resume_argv(state_dir, run_id, IMPLEMENT_RESULT)
        )

    assert payload["action"] == "escalate"
    code, payload = run_cli(capsys, resume_argv(state_dir, run_id, ESCALATE_RESULT))

    assert code == 0
    assert payload["status"] == "completed"
    assert payload["outcome"] == "escalated"


def test_no_frontend_flag_reaches_the_selector(capsys, state_dir, tmp_path):
    path = write_backlog(tmp_path, [entry("gh-ui", touches_frontend=True)])

    code, payload = run_cli(capsys, start_argv(state_dir, path, "--no-frontend"))

    assert code == 0
    assert payload["outcome"] == "idle"


def test_exclude_reaches_the_selector(capsys, state_dir, backlog):
    code, payload = run_cli(capsys, start_argv(state_dir, backlog, "--exclude", "gh-7"))

    assert code == 0
    assert payload["outcome"] == "idle"


# --------------------------------------------------------------------------
# Preflight
# --------------------------------------------------------------------------


def blocked_preflight(*blockers):
    def _preflight(*, runner=None, repo_root=None, loop_prs_opened_today=0, total_prs_opened_today=0):
        return gates.PreflightReport(ok=False, blockers=list(blockers))

    return _preflight


def test_start_refuses_to_run_when_preflight_reports_blockers(
    capsys, monkeypatch, state_dir, backlog
):
    monkeypatch.setattr(
        gates,
        "preflight",
        blocked_preflight("Working tree is dirty (2 untracked file(s))"),
    )

    code, payload = run_cli(
        capsys, ["start", "--state-dir", state_dir, "--backlog", backlog]
    )

    # Blocked is a legitimate answer, not a driver failure.
    assert code == 0
    assert payload["status"] == "blocked"
    assert payload["blockers"] == ["Working tree is dirty (2 untracked file(s))"]
    assert payload["journal"] == []


def test_a_blocked_start_never_creates_a_run(
    capsys, monkeypatch, state_dir, backlog
):
    monkeypatch.setattr(gates, "preflight", blocked_preflight("on the default branch"))

    _, payload = run_cli(
        capsys, ["start", "--state-dir", state_dir, "--backlog", backlog]
    )

    assert "run_id" not in payload
    assert not os.path.isdir(state_dir)


def test_a_blocked_start_reports_every_blocker_at_once(
    capsys, monkeypatch, state_dir, backlog
):
    monkeypatch.setattr(
        gates, "preflight", blocked_preflight("branch", "dirty", "deploy budget")
    )

    _, payload = run_cli(
        capsys, ["start", "--state-dir", state_dir, "--backlog", backlog]
    )

    assert payload["blockers"] == ["branch", "dirty", "deploy budget"]


def test_a_clean_preflight_lets_the_run_proceed(
    capsys, green_ci, monkeypatch, state_dir, backlog
):
    monkeypatch.setattr(
        gates,
        "preflight",
        lambda **_kwargs: gates.PreflightReport(ok=True, blockers=[]),
    )

    code, payload = run_cli(
        capsys, ["start", "--state-dir", state_dir, "--backlog", backlog]
    )

    assert code == 0
    assert payload["status"] == "awaiting_action"


def test_skip_preflight_really_bypasses_the_check(
    capsys, green_ci, monkeypatch, state_dir, backlog
):
    """Monkeypatched to explode — if it is still called, the bypass is fake."""

    def _explode(**_kwargs):
        raise AssertionError("preflight must not run under --skip-preflight")

    monkeypatch.setattr(gates, "preflight", _explode)

    code, payload = run_cli(capsys, start_argv(state_dir, backlog))

    assert code == 0
    assert payload["status"] == "awaiting_action"


def test_preflight_sees_the_deploy_quota_the_caller_passed(
    capsys, monkeypatch, state_dir, backlog
):
    seen = {}

    def _preflight(*, runner=None, repo_root=None, loop_prs_opened_today=0, total_prs_opened_today=0):
        seen["prs_opened_today"] = loop_prs_opened_today
        return gates.PreflightReport(ok=False, blockers=["stop"])

    monkeypatch.setattr(gates, "preflight", _preflight)

    run_cli(
        capsys,
        [
            "start",
            "--state-dir",
            state_dir,
            "--backlog",
            backlog,
            "--prs-opened-today",
            "4",
        ],
    )

    assert seen == {"prs_opened_today": 4}


def test_resume_does_not_run_preflight(capsys, green_ci, monkeypatch, state_dir, backlog):
    """A run already past the gate must not be re-blocked mid-flight."""
    _, started = run_cli(capsys, start_argv(state_dir, backlog))

    def _explode(**_kwargs):
        raise AssertionError("resume must not re-run preflight")

    monkeypatch.setattr(gates, "preflight", _explode)

    code, resumed = run_cli(
        capsys, resume_argv(state_dir, started["run_id"], IMPLEMENT_RESULT)
    )

    assert code == 0
    assert resumed["action"] == "open_pr"
