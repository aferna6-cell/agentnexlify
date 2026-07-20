"""Golden-question eval harness (enterprise-audit item 2) — contracts.

The harness is deterministic: a question passes iff every expected phrase
appears (case-insensitive) in the compiled widget knowledge + FAQs. A
regression = passed last run, fails now → one activity_log alert.
"""

from unittest.mock import MagicMock, patch

from backend.services import kb_evals


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows, sink=None):
        self._rows = rows
        self._sink = sink if sink is not None else []

    def __getattr__(self, name):
        def _method(*args, **kwargs):
            self._sink.append((name, args))
            if name == "execute":
                return _Result(self._rows)
            return self

        return _method


def _db(rows_by_table, sink=None):
    db = MagicMock()
    db.table.side_effect = lambda name: _Query(
        rows_by_table.get(name, []), sink
    )
    return db


class TestEvaluateQuestion:
    def test_passes_when_all_phrases_grounded(self):
        result = kb_evals.evaluate_question(
            "we are open monday to friday 8am-5pm. brake pads from $180.",
            {"id": "q1", "question": "hours?", "expected_phrases": ["8am-5pm"]},
        )
        assert result["passed"] is True
        assert result["missing_phrases"] == []

    def test_fails_and_names_missing_phrase(self):
        result = kb_evals.evaluate_question(
            "we are open monday to friday.",
            {
                "id": "q1",
                "question": "price?",
                "expected_phrases": ["Monday", "$180"],
            },
        )
        assert result["passed"] is False
        assert result["missing_phrases"] == ["$180"]

    def test_matching_is_case_insensitive(self):
        result = kb_evals.evaluate_question(
            "call keys koffee anytime",
            {"id": "q1", "question": "name?", "expected_phrases": ["Keys Koffee"]},
        )
        assert result["passed"] is True

    def test_no_phrases_means_fail_not_vacuous_pass(self):
        result = kb_evals.evaluate_question(
            "anything", {"id": "q1", "question": "?", "expected_phrases": []}
        )
        assert result["passed"] is False


class TestGroundingCorpus:
    def test_merges_kb_and_faqs_lowercased(self):
        db = _db(
            {
                "widget_configs": [{"knowledge_base": "We Fix BRAKES"}],
                "faq_entries": [{"question": "Hours?", "answer": "8am-5pm DAILY"}],
            }
        )
        corpus = kb_evals.grounding_corpus(db, "t1")
        assert "we fix brakes" in corpus
        assert "8am-5pm daily" in corpus

    def test_read_failures_degrade_to_empty(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("down")
        assert kb_evals.grounding_corpus(db, "t1") == ""


class TestRunEvals:
    def _tables(self, questions, prev_results=None):
        return {
            "tenant_eval_questions": questions,
            "tenant_eval_runs": (
                [{"results": prev_results}] if prev_results is not None else []
            ),
            "widget_configs": [{"knowledge_base": "open 8am-5pm weekdays"}],
            "faq_entries": [],
        }

    def test_run_persists_summary_and_counts(self):
        sink: list = []
        questions = [
            {"id": "q1", "question": "hours?", "expected_phrases": ["8am-5pm"]},
            {"id": "q2", "question": "price?", "expected_phrases": ["$99"]},
        ]
        with patch.object(
            kb_evals, "get_service_supabase",
            return_value=_db(self._tables(questions), sink),
        ), patch.object(kb_evals, "log_activity") as activity:
            summary = kb_evals.run_evals("t1", trigger="manual")
        assert summary["total"] == 2
        assert summary["passed"] == 1
        assert summary["failed"] == 1
        assert summary["regressions"] == 0
        # No regression on a first run — q2 never passed before.
        activity.assert_not_called()
        assert any(name == "insert" for name, _ in sink)

    def test_regression_fires_activity_alert(self):
        questions = [
            {"id": "q2", "question": "price?", "expected_phrases": ["$99"]}
        ]
        prev = [{"question_id": "q2", "passed": True}]
        with patch.object(
            kb_evals, "get_service_supabase",
            return_value=_db(self._tables(questions, prev_results=prev)),
        ), patch.object(kb_evals, "log_activity") as activity:
            summary = kb_evals.run_evals("t1", trigger="kb_compile")
        assert summary["regressions"] == 1
        activity.assert_called_once()
        assert (
            activity.call_args.kwargs["activity_type"] == "kb_eval_regression"
        )

    def test_still_failing_question_is_not_a_regression(self):
        questions = [
            {"id": "q2", "question": "price?", "expected_phrases": ["$99"]}
        ]
        prev = [{"question_id": "q2", "passed": False}]
        with patch.object(
            kb_evals, "get_service_supabase",
            return_value=_db(self._tables(questions, prev_results=prev)),
        ), patch.object(kb_evals, "log_activity") as activity:
            summary = kb_evals.run_evals("t1")
        assert summary["regressions"] == 0
        activity.assert_not_called()

    def test_question_read_failure_returns_empty_summary(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("down")
        with patch.object(kb_evals, "get_service_supabase", return_value=db):
            summary = kb_evals.run_evals("t1")
        assert summary == {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "regressions": 0,
            "results": [],
        }


class TestCompileHook:
    def test_hook_never_raises(self):
        with patch.object(
            kb_evals, "run_evals", side_effect=RuntimeError("boom")
        ):
            kb_evals.run_evals_after_compile("t1")  # must not raise
