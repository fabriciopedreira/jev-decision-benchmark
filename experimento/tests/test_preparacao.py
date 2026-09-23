import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "preparar_dados.py"
SPEC = importlib.util.spec_from_file_location("preparar_dados", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PrepareWiCETest(unittest.TestCase):
    def test_partial_support_is_not_attributable_and_gold_stays_separate(self):
        source = [{
            "claim": "A and B",
            "evidence": ["A"],
            "label": "partially_supported",
            "meta": {"id": "dev1", "claim_title": "Page", "claim_context": "Context"},
        }]
        states, manifest, labels, exclusions = MODULE.prepare_records(source, "calibration")
        self.assertEqual(len(states), 1)
        self.assertEqual(labels[0]["published_label"], "NOT_ATTRIBUTABLE")
        self.assertNotIn("label", states[0]["state"])
        self.assertEqual(states[0]["state"]["claim_context"], "Context")
        self.assertEqual(manifest[0]["split"], "calibration")
        self.assertEqual(exclusions, [])

    def test_exclusion_is_independent_of_label(self):
        source = [{
            "claim": "C",
            "evidence": ["x" * (MODULE.MAX_EVIDENCE_CHARS + 1)],
            "label": "supported",
            "meta": {"id": "test1", "claim_title": "Page", "claim_context": ""},
        }]
        states, manifest, labels, exclusions = MODULE.prepare_records(source, "test")
        self.assertEqual((states, manifest, labels), ([], [], []))
        self.assertEqual(exclusions[0]["reason"], "evidence_over_60000_chars")

    def test_duplicate_id_fails(self):
        row = {
            "claim": "C", "evidence": ["C"], "label": "supported",
            "meta": {"id": "test1", "claim_title": "Page", "claim_context": ""},
        }
        with self.assertRaisesRegex(ValueError, "duplicado"):
            MODULE.prepare_records([row, row], "test")


if __name__ == "__main__":
    unittest.main()
