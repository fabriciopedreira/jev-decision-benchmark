"""Regressões da revisão independente; clientes falsos, sem rede/chaves."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness.core import InputCase, Prediction
from harness.judges import JevJudge
from harness import runner

CASE = InputCase('case', 'calibration', 'fixture', {'claim':'A', 'evidence':['A']}, 'hash', False)


class SafeExecutionTests(unittest.TestCase):
    def test_invalid_probability_is_failure_and_escalates(self):
        for value in (float('inf'), float('-inf'), float('nan'), -0.1, 1.1):
            with self.subTest(value=value):
                response = SimpleNamespace(nouls={'attribution':SimpleNamespace(noul=value)})
                client = SimpleNamespace(system_one=lambda **kwargs:response)
                judge = JevJudge(client=client, noul_factory=lambda **kwargs:kwargs)
                result = judge.classify(CASE)
                self.assertEqual(result.status, 'error')
                calls = []
                route, _, _ = runner.decide_cascade(result, lambda:calls.append(1), .3, .7)
                self.assertEqual((route,calls), ('luna_after_jev',[1]))

    def test_metadata_parent_created_before_client_initialization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            args=SimpleNamespace(execute_external=True,split='calibration',max_cases=1,
                output=root/'results/out.jsonl', metadata_output=root/'metadata/out.json',
                env_file=root/'unused.env',freeze=None)
            dataset=SimpleNamespace(cases=lambda split:[CASE],calibration_labels=lambda:{'case':'ATTRIBUTABLE'})
            def fake_judge(*a,**kw):
                self.assertTrue(args.output.parent.is_dir())
                self.assertTrue(args.metadata_output.parent.is_dir())
                return SimpleNamespace(classify=lambda case:Prediction(case.case_id,'fake','fake','ATTRIBUTABLE',.9,1,'ok'),close=lambda:None)
            with patch.object(runner,'read_env_keys'), patch('harness.core.validate_runtime_versions'), \
                 patch.object(runner,'identity',return_value={}), patch.object(runner,'JevJudge',side_effect=fake_judge), \
                 patch.object(runner,'OpenAIJudge',side_effect=fake_judge):
                runner.execute(args,dataset)
            self.assertEqual(json.loads(args.metadata_output.read_text())['completed_cases'],1)
            self.assertTrue(args.output.is_file())

    def test_bad_destination_fails_before_credentials_or_clients(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'blocked').touch()
            args=SimpleNamespace(execute_external=True,split='calibration',max_cases=1,
                output=root/'results/out.jsonl', metadata_output=root/'blocked/out.json',
                env_file=root/'unused.env',freeze=None)
            dataset=SimpleNamespace(cases=lambda split:[CASE],calibration_labels=lambda:{'case':'ATTRIBUTABLE'})
            with patch.object(runner,'read_env_keys') as credentials, patch.object(runner,'JevJudge') as client:
                with self.assertRaises(FileExistsError):runner.execute(args,dataset)
                credentials.assert_not_called();client.assert_not_called()

    def test_original_freeze_is_not_valid_for_consolidated_code(self):
        root=Path(__file__).resolve().parents[1]
        with self.assertRaisesRegex(ValueError,'novo freeze'):
            runner.verify_freeze(root/'resultados/freeze-original.json',None)

    def test_external_run_requires_explicit_flag(self):
        with self.assertRaisesRegex(SystemExit,'--execute-external'):
            runner.execute(SimpleNamespace(execute_external=False),None)


if __name__=='__main__':unittest.main()
