from datetime import datetime, timedelta, timezone
import unittest

from scripts.teamctl import (
    TeamError,
    active_claims,
    branch_name,
    event_marker,
    extract_events,
    issue_events,
    make_event,
    readiness,
    validate_contract,
)


NOW = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)


def contract():
    return {
        "schema_version": 1,
        "north_star": "Ship trustworthy business outcomes.",
        "agents": {"codex": {}, "fable5": {}, "kimi3": {}},
        "required_reads": [],
        "coordination": {},
        "review": {
            "normal_peer_approvals": 1,
            "risky_peer_approvals": 2,
        },
        "autonomy": {},
        "verification": {},
        "github_actions": {
            "allowed_for_team_work": False,
            "required_commit_marker": "[skip ci]",
        },
    }


def event(kind, agent="codex", lane="api", offset=0, **fields):
    return make_event(
        kind,
        42,
        agent,
        lane,
        f"{kind} summary",
        now=NOW + timedelta(minutes=offset),
        **fields,
    )


class TeamCtlTests(unittest.TestCase):
    def test_event_marker_round_trip(self):
        original = event("update", evidence="tests pass")
        body = f"Visible explanation\n\n{event_marker(original)}"
        self.assertEqual(extract_events([{"body": body}]), [original])

    def test_extract_events_ignores_malformed_markers(self):
        comments = ["<!-- agent-team:event not-json -->", "ordinary comment"]
        self.assertEqual(extract_events(comments), [])

    def test_issue_events_reject_untrusted_comment_authors(self):
        policy = contract()
        policy["coordination"]["trusted_github_actors"] = ["repo-owner"]
        trusted = event("update")
        forged = event("review", agent="fable5", verdict="approve")
        issue = {
            "number": 42,
            "comments": [
                {
                    "author": {"login": "repo-owner"},
                    "body": event_marker(trusted),
                },
                {
                    "author": {"login": "outsider"},
                    "body": event_marker(forged),
                },
            ],
        }
        self.assertEqual(issue_events(issue, policy), [trusted])

    def test_active_claim_is_exclusive_until_release(self):
        claim = event("claim", expires_at="2026-07-20T16:00:00Z")
        self.assertEqual(active_claims([claim], NOW)["api"]["agent"], "codex")

        release = event("release", offset=1)
        self.assertEqual(active_claims([claim, release], NOW), {})

    def test_expired_claim_is_not_active(self):
        claim = event("claim", expires_at="2026-07-20T11:59:00Z")
        self.assertEqual(active_claims([claim], NOW), {})

    def test_handoff_releases_lane_for_receiver_to_claim(self):
        claim = event("claim", expires_at="2026-07-20T16:00:00Z")
        handoff = event("handoff", offset=1, to="kimi3")
        self.assertEqual(active_claims([claim, handoff], NOW), {})

    def test_branch_name_is_safe_and_stable(self):
        self.assertEqual(
            branch_name(42, "Kimi 3", "API Contract!"),
            "team/42/kimi-3/api-contract",
        )

    def test_normal_lane_requires_peer_approval_and_passing_proof(self):
        events = [
            event("claim", agent="codex", expires_at="2026-07-20T16:00:00Z"),
            event("review", agent="fable5", offset=1, verdict="approve"),
            event("proof", agent="codex", offset=2, result="PASS"),
        ]
        result = readiness(events, "api", "normal", contract(), NOW)
        self.assertTrue(result["ready"])
        self.assertEqual(result["approvals"], ["fable5"])

    def test_risky_lane_requires_both_other_agents(self):
        events = [
            event("claim", agent="codex", expires_at="2026-07-20T16:00:00Z"),
            event("review", agent="fable5", offset=1, verdict="approve"),
            event("proof", agent="codex", offset=2, result="PASS"),
        ]
        self.assertFalse(readiness(events, "api", "risky", contract(), NOW)["ready"])

        events.append(event("review", agent="kimi3", offset=3, verdict="approve"))
        self.assertTrue(readiness(events, "api", "risky", contract(), NOW)["ready"])

    def test_latest_review_verdict_wins(self):
        events = [
            event("claim", agent="codex", expires_at="2026-07-20T16:00:00Z"),
            event("review", agent="fable5", offset=1, verdict="approve"),
            event("review", agent="fable5", offset=2, verdict="request_changes"),
            event("proof", agent="codex", offset=3, result="PASS"),
        ]
        self.assertFalse(readiness(events, "api", "normal", contract(), NOW)["ready"])

    def test_self_approval_does_not_count(self):
        events = [
            event("claim", agent="codex", expires_at="2026-07-20T16:00:00Z"),
            event("review", agent="codex", offset=1, verdict="approve"),
            event("proof", agent="codex", offset=2, result="PASS"),
        ]
        self.assertFalse(readiness(events, "api", "normal", contract(), NOW)["ready"])

    def test_update_invalidates_stale_approval_and_proof(self):
        events = [
            event("claim", agent="codex", expires_at="2026-07-20T16:00:00Z"),
            event("review", agent="fable5", offset=1, verdict="approve"),
            event("proof", agent="codex", offset=2, result="PASS"),
            event("update", agent="codex", offset=3),
        ]
        result = readiness(events, "api", "normal", contract(), NOW)
        self.assertFalse(result["ready"])
        self.assertEqual(result["approvals"], [])
        self.assertFalse(result["passing_proof"])

    def test_released_or_expired_lane_cannot_be_ready(self):
        expired = [
            event("claim", agent="codex", expires_at="2026-07-20T11:59:00Z"),
            event("review", agent="fable5", offset=1, verdict="approve"),
            event("proof", agent="codex", offset=2, result="PASS"),
        ]
        self.assertFalse(readiness(expired, "api", "normal", contract(), NOW)["ready"])

        released = [
            event("claim", agent="codex", expires_at="2026-07-20T16:00:00Z"),
            event("review", agent="fable5", offset=1, verdict="approve"),
            event("proof", agent="codex", offset=2, result="PASS"),
            event("release", agent="codex", offset=3),
        ]
        self.assertFalse(readiness(released, "api", "normal", contract(), NOW)["ready"])

    def test_contract_rejects_actions_for_team_work(self):
        invalid = contract()
        invalid["github_actions"]["allowed_for_team_work"] = True
        with self.assertRaisesRegex(TeamError, "GitHub Actions"):
            validate_contract(invalid)


if __name__ == "__main__":
    unittest.main()
