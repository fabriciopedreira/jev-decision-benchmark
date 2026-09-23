from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.core import InputCase, Prediction
from harness.judges import RuleJudge
from harness.runner import Dataset, decide_cascade, run_case


def prediction(case: InputCase, provider: str, probability: float | None, status: str = "ok") -> Prediction:
    return Prediction(
        case_id=case.case_id,
        provider=provider,
        model=provider,
        label=("ATTRIBUTABLE" if probability >= 0.5 else "NOT_ATTRIBUTABLE") if probability is not None else None,
        probability_attributable=probability,
        latency_ms=1,
        status=status,
    )


class FakeJudge:
    def __init__(self, name: str, probability: float, calls: list[str]):
        self.name = name
        self.probability = probability
        self.calls = calls

    def classify(self, case: InputCase) -> Prediction:
        self.calls.append(self.name)
        return prediction(case, self.name, self.probability)


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.case = InputCase("wice:test", "test", "WiCE-claim", {"claim": "A", "evidence": ["A"], "claim_context": ""}, "hash", False)

    def test_dataset_is_valid_and_group_disjoint(self):
        dataset = Dataset()
        self.assertEqual(len(dataset.cases("calibration")), 348)
        self.assertEqual(len(dataset.cases("test")), 355)

    def test_confident_jev_does_not_call_cascade_luna(self):
        calls = []
        judges = {
            "jev": FakeJudge("jev", 0.92, calls),
            "luna": FakeJudge("luna", 1.0, calls),
            "terra": FakeJudge("terra", 1.0, calls),
        }
        row = run_case(self.case, judges, RuleJudge(0.5), negative=0.3, positive=0.7, seed=2)
        self.assertEqual(row["cascade"]["route"], "jev")
        self.assertIsNone(row["cascade"]["luna"])
        self.assertEqual(calls.count("luna"), 1)  # baseline independente

    def test_uncertain_jev_calls_distinct_baseline_and_sequential_cascade_luna(self):
        calls = []
        judges = {
            "jev": FakeJudge("jev", 0.55, calls),
            "luna": FakeJudge("luna", 0.0, calls),
            "terra": FakeJudge("terra", 1.0, calls),
        }
        row = run_case(self.case, judges, RuleJudge(0.5), negative=0.3, positive=0.7, seed=2)
        self.assertEqual(row["cascade"]["route"], "luna_after_jev")
        self.assertEqual(calls.count("luna"), 2)
        self.assertEqual(calls[calls.index("jev") + 1], "luna")
        self.assertEqual(row["cascade"]["final_label"], "NOT_ATTRIBUTABLE")

    def test_jev_failure_escalates(self):
        result = prediction(self.case, "jev", None, "error")
        called = []
        route, luna, final = decide_cascade(result, lambda: called.append(True) or prediction(self.case, "luna", 0.0), 0.3, 0.7)
        self.assertEqual(route, "luna_after_jev")
        self.assertTrue(called)
        self.assertIs(luna, final)


if __name__ == "__main__":
    unittest.main()
