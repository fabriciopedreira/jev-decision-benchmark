from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analisar_wice_v4 import cost, margin_state, short_score
from harness_v3.metrics import score


class AnalyzeV4Tests(unittest.TestCase):
    def test_cache_write_and_hit_prices_are_distinct(self):
        prediction = {
            "usage": {"input_tokens": 1_000, "output_tokens": 10, "cached_input_tokens": 300},
            "raw": {"debug": {"llm_attempts": [{"llm_response": {"usage": {"input_tokens_details": {"cache_write_tokens": 200}}}}]}},
        }
        expected = (500 * 2.0 + 200 * 2.0 * 1.25 + 300 * 0.20 + 10 * 12.0) / 1_000_000
        self.assertAlmostEqual(cost(prediction, "terra"), expected)

    def test_short_bootstrap_metric_matches_full_metric_with_failures(self):
        labels = {"a": "ATTRIBUTABLE", "b": "ATTRIBUTABLE", "c": "NOT_ATTRIBUTABLE", "d": "NOT_ATTRIBUTABLE"}
        rows = [
            {"case_id": "a", "status": "ok", "label": "ATTRIBUTABLE", "latency_ms": 1},
            {"case_id": "b", "status": "error", "label": None, "latency_ms": 1},
            {"case_id": "c", "status": "ok", "label": "ATTRIBUTABLE", "latency_ms": 1},
            {"case_id": "d", "status": "ok", "label": "NOT_ATTRIBUTABLE", "latency_ms": 1},
        ]
        result = score(rows, labels)
        observed = short_score({row["case_id"]: row for row in rows}, labels, list(labels))
        self.assertEqual(observed, (result["macro_f1"], result["false_attributable_rate"], result["failure_rate"]))

    def test_margin_state_keeps_uncertainty_distinct_from_failure(self):
        interval = {"one_sided_95_low": -0.04, "one_sided_95_high": 0.01}
        self.assertEqual(margin_state(interval, -0.01, higher_is_better=True), "inconclusive")
        self.assertEqual(margin_state({"one_sided_95_low": -0.06, "one_sided_95_high": -0.02}, -0.01, higher_is_better=True), "fail")
        self.assertEqual(margin_state({"one_sided_95_low": -0.02, "one_sided_95_high": 0.0}, 0.01, higher_is_better=False), "pass")


if __name__ == "__main__":
    unittest.main()
