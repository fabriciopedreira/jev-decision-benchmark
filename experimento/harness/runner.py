from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from harness.core import InputCase, Prediction
from harness.judges import RuleJudge

from .judges import JevJudge, OpenAIJudge


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
TOPIC_ROOT = EXPERIMENT_ROOT.parent
SNAPSHOT = EXPERIMENT_ROOT / "snapshots/entradas.jsonl"
MANIFEST = EXPERIMENT_ROOT / "snapshots/manifesto.csv"
LABELS = EXPERIMENT_ROOT / "snapshots/gabarito.csv"
PROTOCOL = TOPIC_ROOT / "docs/protocolo-original.md"
SEED = 20260923


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def implementation_hash() -> str:
    paths = [
        EXPERIMENT_ROOT / "preparar_dados.py",
        EXPERIMENT_ROOT / "requirements.txt",
        EXPERIMENT_ROOT / "analisar.py",
        *sorted((EXPERIMENT_ROOT / "harness").glob("*.py")),
    ]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(EXPERIMENT_ROOT)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class Dataset:
    def __init__(self):
        with SNAPSHOT.open(encoding="utf-8") as handle:
            snapshots = [json.loads(line) for line in handle if line.strip()]
        with MANIFEST.open(newline="", encoding="utf-8") as handle:
            self.manifest = list(csv.DictReader(handle))
        self.states = {row["case_id"]: row["state"] for row in snapshots}
        if len(snapshots) != len(self.states) or len(self.manifest) != len(self.states):
            raise ValueError("Quantidade ou IDs de snapshot/manifesto inconsistentes")
        seen = set()
        groups = {"calibration": set(), "test": set()}
        for row in self.manifest:
            case_id = row["case_id"]
            if case_id in seen or case_id not in self.states:
                raise ValueError(f"ID duplicado ou ausente: {case_id}")
            seen.add(case_id)
            if row["split"] not in groups:
                raise ValueError(f"Split inesperado: {row['split']}")
            observed = hashlib.sha256(json.dumps(self.states[case_id], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if observed != row["input_sha256"]:
                raise ValueError(f"Entrada alterada: {case_id}")
            groups[row["split"]].add(row["parent_group_id"])
        if groups["calibration"] & groups["test"]:
            raise ValueError("Grupo vazou entre desenvolvimento e teste")

    def cases(self, split: str) -> list[InputCase]:
        return [
            InputCase(
                case_id=row["case_id"], split=split, source_dataset=row["source_dataset"],
                state=self.states[row["case_id"]], input_sha256=row["input_sha256"], stability=False,
            )
            for row in self.manifest if row["split"] == split
        ]

    def calibration_labels(self) -> dict[str, str]:
        calibration_ids = {case.case_id for case in self.cases("calibration")}
        with LABELS.open(newline="", encoding="utf-8") as handle:
            rows = [row for row in csv.DictReader(handle) if row["case_id"] in calibration_ids]
        labels = {row["case_id"]: row["published_label"] for row in rows}
        if len(labels) != len(calibration_ids):
            raise ValueError("Gabarito de desenvolvimento incompleto")
        return labels


def identity() -> dict:
    return {
        "snapshot_sha256": sha256(SNAPSHOT),
        "manifest_sha256": sha256(MANIFEST),
        "labels_sha256": sha256(LABELS),
        "protocol_sha256": sha256(PROTOCOL),
        "implementation_sha256": implementation_hash(),
    }


def create_freeze(path: Path, dataset: Dataset) -> dict:
    rule = RuleJudge.fit(dataset.cases("calibration"), dataset.calibration_labels())
    payload = {
        **identity(),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "rule_threshold": rule.threshold,
        "cascade_negative_threshold": 0.30,
        "cascade_positive_threshold": 0.70,
        "seed": SEED,
        "models": {"jev": "jev-1.13.0", "luna": "gpt-5.6-luna", "terra": "gpt-5.6-terra"},
        "reasoning": {"luna": "none", "terra": "provider_default"},
        "test_case_count": len(dataset.cases("test")),
        "status": "frozen_before_external_test",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return payload


def verify_freeze(path: Path, dataset: Dataset) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("implementation_sha256") != implementation_hash():
        raise ValueError("Freeze divergente: implementation_sha256. A distribuição consolidada exige um novo freeze; não reutilize o registro da execução original.")
    for key, value in identity().items():
        if payload.get(key) != value:
            raise ValueError(f"Freeze divergente: {key}")
    if payload.get("test_case_count") != len(dataset.cases("test")):
        raise ValueError("Quantidade de casos divergiu do freeze")
    if payload.get("cascade_negative_threshold") != 0.30 or payload.get("cascade_positive_threshold") != 0.70:
        raise ValueError("Política de cascata alterada")
    return payload


def read_env_keys(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo de credenciais ausente: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.fullmatch(r"(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)", stripped)
        if match is None:
            raise ValueError("Linha .env não reconhecida; nenhuma expressão shell é executada")
        key, value = match.groups()
        if key not in ("TYPESAFE_API_KEY", "OPENAI_API_KEY"):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)
    for key in ("TYPESAFE_API_KEY", "OPENAI_API_KEY"):
        if not os.environ.get(key):
            raise ValueError(f"Credencial {key} não configurada")


def decide_cascade(jev: Prediction, luna_call, negative: float, positive: float) -> tuple[str, Prediction | None, Prediction]:
    probability = jev.probability_attributable
    if jev.status == "ok" and probability is not None and (probability <= negative or probability >= positive):
        return "jev", None, jev
    luna = luna_call()
    return "luna_after_jev", luna, luna


def run_case(case: InputCase, judges: dict, rule: RuleJudge, *, negative: float, positive: float, seed: int) -> dict:
    blocks = ["luna_baseline", "terra_baseline", "cascade"]
    random.Random(seed ^ int(hashlib.sha256(case.case_id.encode()).hexdigest()[:8], 16)).shuffle(blocks)
    output: dict = {"case_id": case.case_id, "input_sha256": case.input_sha256, "block_order": blocks}
    for block in blocks:
        if block == "luna_baseline":
            output[block] = asdict(judges["luna"].classify(case))
        elif block == "terra_baseline":
            output[block] = asdict(judges["terra"].classify(case))
        else:
            started = time.perf_counter()
            jev = judges["jev"].classify(case)
            route, cascade_luna, final = decide_cascade(
                jev, lambda: judges["luna"].classify(case), negative, positive,
            )
            output["cascade"] = {
                "route": route,
                "jev": asdict(jev),
                "luna": asdict(cascade_luna) if cascade_luna is not None else None,
                "final_label": final.label if final.status == "ok" else None,
                "status": final.status,
                "latency_ms": (time.perf_counter() - started) * 1000,
            }
    output["rule"] = asdict(rule.classify(case))
    return output


def execute(args, dataset: Dataset) -> None:
    if not args.execute_external:
        raise SystemExit("Chamadas externas exigem --execute-external")
    if args.split == "test":
        if args.freeze is None:
            raise SystemExit("Teste exige --freeze")
        policy = verify_freeze(args.freeze, dataset)
        if args.max_cases is not None:
            raise SystemExit("Teste não permite --max-cases")
    else:
        policy = {"rule_threshold": RuleJudge.fit(dataset.cases("calibration"), dataset.calibration_labels()).threshold,
                  "cascade_negative_threshold": 0.30, "cascade_positive_threshold": 0.70}
    if args.output.exists() or args.metadata_output.exists():
        raise FileExistsError("Resultado ou metadados já existem; não sobrescrever")
    if args.output.resolve() == args.metadata_output.resolve():
        raise ValueError("Resultado e metadados precisam de destinos distintos")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.metadata_output.parent.mkdir(parents=True, exist_ok=True)
    read_env_keys(args.env_file)
    from harness.core import validate_runtime_versions

    validate_runtime_versions(require_openai=True)
    cases = dataset.cases(args.split)
    random.Random(SEED).shuffle(cases)
    if args.max_cases is not None:
        if args.max_cases < 1:
            raise ValueError("--max-cases precisa ser positivo")
        cases = cases[:args.max_cases]
    rule = RuleJudge(float(policy["rule_threshold"]))
    judges = {
        "jev": JevJudge(),
        "luna": OpenAIJudge("gpt-5.6-luna", reasoning_effort="none"),
        "terra": OpenAIJudge("gpt-5.6-terra", reasoning_effort=None),
    }
    started = datetime.now(timezone.utc)
    try:
        with args.output.open("x", encoding="utf-8") as handle:
            for index, case in enumerate(cases, 1):
                result = run_case(case, judges, rule,
                                  negative=policy["cascade_negative_threshold"],
                                  positive=policy["cascade_positive_threshold"], seed=SEED)
                handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
                handle.flush()
                if index % 25 == 0 or index == len(cases):
                    print(json.dumps({"completed": index, "total": len(cases), "split": args.split}), flush=True)
    finally:
        for judge in judges.values():
            judge.close()
    with args.output.open(encoding="utf-8") as handle:
        completed_cases = sum(1 for line in handle if line.strip())
    metadata = {
        "started_at_utc": started.isoformat(),
        "ended_at_utc": datetime.now(timezone.utc).isoformat(),
        "split": args.split,
        "expected_cases": len(cases),
        "completed_cases": completed_cases,
        "identity": identity(),
        "freeze_sha256": sha256(args.freeze) if args.freeze else None,
        "result_sha256": sha256(args.output),
        "seed": SEED,
        "concurrency": 1,
        "transport_retries": 0,
        "malformed_retries": 0,
        "models": {"jev": "jev-1.13.0", "luna": "gpt-5.6-luna", "terra": "gpt-5.6-terra"},
        "luna_reasoning": "none",
        "terra_reasoning": "provider_default",
    }
    with args.metadata_output.open("x", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("validate")
    freeze = actions.add_parser("freeze")
    freeze.add_argument("--output", type=Path, required=True)
    run = actions.add_parser("run")
    run.add_argument("--split", choices=("calibration", "test"), required=True)
    run.add_argument("--freeze", type=Path)
    run.add_argument("--max-cases", type=int)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--metadata-output", type=Path, required=True)
    run.add_argument("--env-file", type=Path, default=Path.cwd() / ".env")
    run.add_argument("--execute-external", action="store_true")
    args = parser.parse_args()
    dataset = Dataset()
    if args.action == "validate":
        print(json.dumps({"identity": identity(), "calibration": len(dataset.cases("calibration")),
                          "test": len(dataset.cases("test"))}, indent=2, sort_keys=True))
    elif args.action == "freeze":
        print(json.dumps(create_freeze(args.output, dataset), indent=2, sort_keys=True))
    else:
        execute(args, dataset)


if __name__ == "__main__":
    main()
