"""Unit tests for scripts/autonomy/gates.py — the loop's deterministic safety layer.

Contract under test:

  1. A red gate is DATA. `run_local_ci` / `run_quick_check` never raise on a
     non-zero exit, and the summary carries enough tail to name the gate that
     failed.
  2. A gate that never finishes is also data — timeout returns passed=False
     with TIMEOUT_RETURNCODE, so the loop cannot mistake "unverified" for green.
  3. `git_state` reports the working copy honestly, including the two states
     that matter most: no upstream (fresh loop branch) and a dirty tree.
  4. `deploy_budget_remaining` never lets the loop past the Vercel cap that the
     2026-06-23 incident proved reachable.
  5. `migration_number_conflict` sees numbers claimed by open PRs, which is the
     exact information the 188 collision (PR #575 vs #599) lacked.
  6. `preflight` composes the above into human-actionable blockers.

Every subprocess is faked. These tests run the gates without running CI.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from scripts.autonomy.gates import (  # noqa: E402
    DEFAULT_MAX_PRS_PER_DAY,
    deploy_budget_remaining,
    git_state,
    migration_number_conflict,
    preflight,
    run_local_ci,
    run_quick_check,
)
from scripts.autonomy.runner import (  # noqa: E402
    SPAWN_FAILED_RETURNCODE,
    SUMMARY_LINES,
    TIMEOUT_RETURNCODE,
    CommandResult,
)


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------


def make_runner(handler):
    """Wrap ``handler(command) -> CommandResult`` and record every invocation."""

    def run(command, *, cwd=None, timeout=None):
        run.calls.append({"command": list(command), "cwd": cwd, "timeout": timeout})
        return handler(list(command))

    run.calls = []
    return run


def fixed_runner(returncode=0, stdout=""):
    return make_runner(lambda _cmd: CommandResult(returncode=returncode, stdout=stdout))


def raising_runner(exc):
    def handler(_cmd):
        raise exc

    return make_runner(handler)


def git_runner(
    *,
    branch="claude/agent-loop",
    branch_rc=0,
    status="",
    status_rc=0,
    sha="a1b2c3d4",
    sha_rc=0,
    upstream="0\t0",
    upstream_rc=0,
):
    """A fake `git` whose four subcommands answer independently."""

    def handler(command):
        assert command[0] == "git"
        sub = command[1]
        if sub == "rev-parse" and "--abbrev-ref" in command:
            return CommandResult(branch_rc, branch + "\n")
        if sub == "rev-parse":
            return CommandResult(sha_rc, sha + "\n")
        if sub == "status":
            return CommandResult(status_rc, status)
        if sub == "rev-list":
            return CommandResult(upstream_rc, upstream)
        raise AssertionError(f"unexpected git subcommand: {command}")

    return make_runner(handler)


CI_FAIL_OUTPUT = "\n".join(
    [f"noise line {i}" for i in range(200)]
    + [
        "==================== CI LOCAL SUMMARY ====================",
        "  PASS  diff hygiene (git diff --check)",
        "  FAIL  migration numbering",
        "==========================================================",
        "RESULT: FAIL (1 required gate(s) failed)",
    ]
)


# --------------------------------------------------------------------------
# run_local_ci
# --------------------------------------------------------------------------


def test_run_local_ci_passing_gate():
    runner = fixed_runner(0, "RESULT: PASS (20 required gates green)")

    result = run_local_ci(runner=runner)

    assert result.passed is True
    assert result.name == "local-ci"
    assert result.returncode == 0
    assert "RESULT: PASS" in result.summary
    assert result.duration_seconds >= 0
    assert runner.calls[0]["command"] == ["bash", "scripts/ci_local.sh", "origin/main"]
    assert runner.calls[0]["timeout"] == 3600


def test_run_local_ci_forwards_compare_ref_and_timeout():
    runner = fixed_runner(0, "ok")

    run_local_ci("origin/develop", runner=runner, timeout=60)

    assert runner.calls[0]["command"][-1] == "origin/develop"
    assert runner.calls[0]["timeout"] == 60


def test_run_local_ci_failing_gate_is_data_not_an_exception():
    runner = fixed_runner(1, CI_FAIL_OUTPUT)

    result = run_local_ci(runner=runner)

    assert result.passed is False
    assert result.returncode == 1
    # The whole point of keeping the tail: the failing gate must be named.
    assert "FAIL  migration numbering" in result.summary
    assert "RESULT: FAIL" in result.summary


def test_run_local_ci_summary_is_bounded_to_the_tail():
    runner = fixed_runner(1, CI_FAIL_OUTPUT)

    result = run_local_ci(runner=runner)

    assert len(result.summary.splitlines()) <= SUMMARY_LINES
    assert "noise line 0" not in result.summary


def test_run_local_ci_timeout_returns_unverified_rather_than_raising():
    runner = raising_runner(
        subprocess.TimeoutExpired(cmd=["bash", "scripts/ci_local.sh"], timeout=5)
    )

    result = run_local_ci(runner=runner, timeout=5)

    assert result.passed is False
    assert result.returncode == TIMEOUT_RETURNCODE
    assert "TIMEOUT" in result.summary
    assert "5" in result.summary


def test_run_local_ci_missing_interpreter_does_not_crash_the_loop():
    runner = raising_runner(FileNotFoundError("bash"))

    result = run_local_ci(runner=runner)

    assert result.passed is False
    assert result.returncode == SPAWN_FAILED_RETURNCODE
    assert "COULD NOT START" in result.summary


def test_run_local_ci_empty_output_still_yields_a_summary():
    result = run_local_ci(runner=fixed_runner(1, "   \n  \n"))

    assert result.passed is False
    assert result.summary == "(no output)"


# --------------------------------------------------------------------------
# run_quick_check
# --------------------------------------------------------------------------


def test_run_quick_check_passing_gate():
    runner = fixed_runner(0, "all checks passed")

    result = run_quick_check(runner=runner)

    assert result.passed is True
    assert result.name == "quick-check"
    assert runner.calls[0]["command"] == ["npm", "run", "check:quick", "--silent"]
    assert runner.calls[0]["timeout"] == 900


def test_run_quick_check_failing_gate_carries_the_error():
    runner = fixed_runner(2, "check:quick failed: schema drift detected")

    result = run_quick_check(runner=runner)

    assert result.passed is False
    assert result.returncode == 2
    assert "schema drift detected" in result.summary


def test_run_quick_check_timeout():
    runner = raising_runner(subprocess.TimeoutExpired(cmd=["npm"], timeout=900))

    result = run_quick_check(runner=runner)

    assert result.passed is False
    assert result.returncode == TIMEOUT_RETURNCODE
    assert "TIMEOUT" in result.summary


# --------------------------------------------------------------------------
# git_state
# --------------------------------------------------------------------------


def test_git_state_clean_branch_with_upstream():
    runner = git_runner(branch="claude/loop", sha="deadbeef", upstream="2\t3")

    state = git_state(runner=runner)

    assert state.branch == "claude/loop"
    assert state.is_clean is True
    assert state.head_sha == "deadbeef"
    assert state.untracked_count == 0
    assert state.behind == 2
    assert state.ahead == 3


def test_git_state_without_upstream_degrades_to_zero_zero():
    # `git rev-list @{u}...HEAD` on a branch with no upstream exits non-zero.
    runner = git_runner(
        upstream_rc=128,
        upstream="fatal: no upstream configured for branch 'claude/loop'",
    )

    state = git_state(runner=runner)

    assert state.ahead == 0
    assert state.behind == 0
    assert state.is_clean is True


def test_git_state_dirty_tree_counts_untracked_separately():
    runner = git_runner(
        status=" M backend/main.py\n?? scratch.py\n?? notes.md\n",
    )

    state = git_state(runner=runner)

    assert state.is_clean is False
    assert state.untracked_count == 2


def test_git_state_unreadable_status_is_never_reported_as_clean():
    runner = git_runner(status_rc=128, status="fatal: not a git repository")

    state = git_state(runner=runner)

    assert state.is_clean is False


def test_git_state_detached_head_reports_head_as_branch():
    runner = git_runner(branch="HEAD")

    assert git_state(runner=runner).branch == "HEAD"


def test_git_state_forwards_cwd_to_every_git_call(tmp_path):
    runner = git_runner()

    git_state(runner=runner, cwd=tmp_path)

    assert len(runner.calls) == 4
    assert all(call["cwd"] == tmp_path for call in runner.calls)


def test_git_state_survives_git_being_absent():
    state = git_state(runner=raising_runner(FileNotFoundError("git")))

    assert state.branch == ""
    assert state.head_sha == ""
    assert state.is_clean is False


def test_git_state_ignores_malformed_upstream_counts():
    runner = git_runner(upstream="not-a-count")

    state = git_state(runner=runner)

    assert (state.ahead, state.behind) == (0, 0)


# --------------------------------------------------------------------------
# deploy_budget_remaining
# --------------------------------------------------------------------------


def test_deploy_budget_under_cap():
    assert deploy_budget_remaining(0) == DEFAULT_MAX_PRS_PER_DAY
    assert deploy_budget_remaining(1) == DEFAULT_MAX_PRS_PER_DAY - 1


def test_deploy_budget_at_cap_is_zero():
    assert deploy_budget_remaining(DEFAULT_MAX_PRS_PER_DAY) == 0


def test_deploy_budget_over_cap_clamps_to_zero():
    # The 2026-06-23 run opened 11. Never hand back a negative allowance.
    assert deploy_budget_remaining(11) == 0


def test_deploy_budget_honours_a_custom_cap():
    assert deploy_budget_remaining(3, max_prs_per_day=10) == 7
    assert deploy_budget_remaining(3, max_prs_per_day=2) == 0


def test_deploy_budget_ignores_nonsense_negative_counts():
    assert deploy_budget_remaining(-5) == DEFAULT_MAX_PRS_PER_DAY


# --------------------------------------------------------------------------
# migration_number_conflict
# --------------------------------------------------------------------------


def make_migrations(tmp_path, numbers, separator="_"):
    directory = tmp_path / "migrations"
    directory.mkdir(exist_ok=True)
    for number in numbers:
        (directory / f"{number:03d}{separator}thing.sql").write_text("-- sql\n")
    return tmp_path


def test_migration_no_conflict_returns_none(tmp_path):
    root = make_migrations(tmp_path, [186, 187])

    assert migration_number_conflict(root, 188) is None


def test_migration_conflict_with_existing_file(tmp_path):
    root = make_migrations(tmp_path, [186, 187, 188])

    assert migration_number_conflict(root, 188) == 189


def test_migration_conflict_via_open_pr_claim(tmp_path):
    # The real 188 collision: nothing on disk, but PR #575 already holds it.
    root = make_migrations(tmp_path, [186, 187])

    assert migration_number_conflict(root, 188, extra_claimed=[188]) == 189


def test_migration_next_free_skips_a_run_of_claimed_numbers(tmp_path):
    root = make_migrations(tmp_path, [186, 187, 188])

    assert migration_number_conflict(root, 188, extra_claimed=[189, 190]) == 191


def test_migration_suggestion_never_reuses_a_gap(tmp_path):
    # 187 is missing, but a gap usually means a migration is in flight.
    root = make_migrations(tmp_path, [185, 186, 188])

    assert migration_number_conflict(root, 188) == 189


def test_migration_scan_tolerates_dash_separated_filenames(tmp_path):
    # migrations/081-kb-articles-and-sources.sql exists in the real repo.
    root = make_migrations(tmp_path, [81], separator="-")

    assert migration_number_conflict(root, 81) == 82


def test_migration_ignores_non_numbered_files(tmp_path):
    root = make_migrations(tmp_path, [186])
    (root / "migrations" / "README.md").write_text("notes\n")
    (root / "migrations" / "rollback_thing.sql").write_text("-- sql\n")

    assert migration_number_conflict(root, 186) == 187


def test_migration_missing_directory_reports_no_conflict(tmp_path):
    assert migration_number_conflict(tmp_path, 1) is None


def test_migration_missing_directory_still_honours_pr_claims(tmp_path):
    assert migration_number_conflict(tmp_path, 1, extra_claimed=[1]) == 2


# --------------------------------------------------------------------------
# preflight
# --------------------------------------------------------------------------


def test_preflight_all_good():
    report = preflight(runner=git_runner(), prs_opened_today=0)

    assert report.ok is True
    assert report.blockers == []


def test_preflight_blocks_on_the_default_branch():
    report = preflight(runner=git_runner(branch="main"))

    assert report.ok is False
    assert len(report.blockers) == 1
    assert "main" in report.blockers[0]
    assert "working branch" in report.blockers[0]


def test_preflight_blocks_on_a_dirty_tree():
    report = preflight(runner=git_runner(status=" M backend/main.py\n?? tmp.txt\n"))

    assert report.ok is False
    assert any("dirty" in blocker for blocker in report.blockers)
    assert any("stash" in blocker for blocker in report.blockers)


def test_preflight_blocks_when_the_deploy_budget_is_spent():
    report = preflight(runner=git_runner(), prs_opened_today=DEFAULT_MAX_PRS_PER_DAY)

    assert report.ok is False
    assert any("Deploy budget" in blocker for blocker in report.blockers)


def test_preflight_blocks_on_detached_head():
    report = preflight(runner=git_runner(branch="HEAD"))

    assert report.ok is False
    assert any("detached" in blocker for blocker in report.blockers)


def test_preflight_reports_every_blocker_at_once():
    report = preflight(
        runner=git_runner(branch="main", status="?? scratch.py\n"),
        prs_opened_today=99,
    )

    assert report.ok is False
    assert len(report.blockers) == 3


def test_preflight_reads_git_state_in_the_given_repo_root(tmp_path):
    runner = git_runner()

    preflight(runner=runner, repo_root=tmp_path)

    assert all(call["cwd"] == tmp_path for call in runner.calls)
