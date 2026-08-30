"""QA gate: validation-v3 stays independent of train / frozen / v1 / v2.

Runnable with stdlib unittest (main-only checkout) or pytest:

    python3 -m unittest ml.routing.tests.test_validation_v3_leakage
    python3 -m pytest ml/routing/tests/test_validation_v3_leakage.py -q
"""

from __future__ import annotations

import json
import sys
import unittest
from collections import Counter
from pathlib import Path

AUTHORING = Path(__file__).resolve().parents[1] / "authoring"
sys.path.insert(0, str(AUTHORING))

from check_validation_v3_leakage import check, load_v3  # noqa: E402

V3_PATH = Path(__file__).resolve().parents[3] / "agent-service/evals/datasets/validation/validation-v3.json"
DEPARTMENTS = {
    "accounting",
    "admin_records",
    "customer_service",
    "invoicing",
    "marketing",
    "operations",
    "people",
    "sales",
}


class ValidationV3LeakageTests(unittest.TestCase):
    def test_validation_v3_exists_and_is_sized(self) -> None:
        self.assertTrue(V3_PATH.is_file())
        payload = json.loads(V3_PATH.read_text())
        self.assertEqual(payload["dataset_version"], "action-eval-validation-v3")
        self.assertFalse(payload.get("not_for_model_selection"))
        self.assertTrue(payload.get("frozen"))
        self.assertIn("2026-08-30", payload.get("selection_authorization", ""))
        n = len(payload["cases"])
        self.assertGreaterEqual(n, 150, f"honest n={n} below 150")
        self.assertLessEqual(n, 250, f"honest n={n} above 250")

    def test_eight_labels_no_none_complete_pairs(self) -> None:
        cases = load_v3()
        depts = Counter(c["department_label"] for c in cases)
        self.assertEqual(set(depts), DEPARTMENTS)
        self.assertNotIn("none", depts)
        for c in cases:
            self.assertEqual(c["department_label"], c["expected_department"])
            self.assertIn(c["department_label"], DEPARTMENTS)
        pairs: dict[str, list[str]] = {}
        for c in cases:
            if c.get("pair_id"):
                pairs.setdefault(c["pair_id"], []).append(c["expected_department"])
        self.assertTrue(pairs, "expected at least one hard-negative pair")
        for pid, depts_in_pair in pairs.items():
            self.assertEqual(len(depts_in_pair), 2, f"{pid} must be a true pair, has {len(depts_in_pair)}")
            self.assertGreaterEqual(len(set(depts_in_pair)), 2, f"{pid} does not cross departments")

    def test_leakage_drop_rules_clean(self) -> None:
        report = check(load_v3())
        self.assertTrue(report["clean"], report.get("drop_examples"))
        self.assertEqual(report["n_dropped_on_this_pass"], 0)
        self.assertFalse(report["split_pairs"])
        self.assertFalse(report["none_labels"])
        self.assertEqual(report["pair_size_histogram"], {2: report["pair_count"]})

    def test_rationale_is_documentation_only(self) -> None:
        for c in load_v3():
            self.assertIn("rationale", c)
            self.assertTrue(c["ask"].strip())
            self.assertTrue(c["rationale"].strip())


if __name__ == "__main__":
    unittest.main()
