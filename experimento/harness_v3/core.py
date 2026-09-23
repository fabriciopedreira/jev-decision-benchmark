from __future__ import annotations

import csv
import hashlib
import json
import platform
from datetime import datetime, timezone
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


LABELS = ("ATTRIBUTABLE", "NOT_ATTRIBUTABLE")


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def implementation_sha256(experiment_root: Path) -> str:
    paths = [
        experiment_root / "requirements.txt",
        experiment_root / "preparar_attributionbench_v3.py",
        *sorted((experiment_root / "harness_v3").glob("*.py")),
    ]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(experiment_root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


@dataclass(frozen=True)
class InputCase:
    case_id: str
    split: str
    source_dataset: str
    state: dict
    input_sha256: str
    stability: bool


@dataclass(frozen=True)
class Prediction:
    case_id: str
    provider: str
    model: str
    label: str | None
    probability_attributable: float | None
    latency_ms: float
    status: str
    error_type: str | None = None
    usage: dict | None = None
    raw: dict | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


class Dataset:
    def __init__(self, snapshot: Path, manifest: Path, labels: Path | None = None):
        self.snapshot = snapshot
        self.manifest = manifest
        self.labels_path = labels
        with manifest.open(newline="", encoding="utf-8") as handle:
            self.rows = list(csv.DictReader(handle))
        with snapshot.open(encoding="utf-8") as handle:
            items = [json.loads(line) for line in handle if line.strip()]
        self.states = {item["case_id"]: item["state"] for item in items}
        self.label_map = None
        if labels is not None:
            with labels.open(newline="", encoding="utf-8") as handle:
                label_rows = list(csv.DictReader(handle))
            self.label_map = {row["case_id"]: row["published_label"] for row in label_rows}
            if len(label_rows) != len(self.label_map):
                raise ValueError("Case IDs duplicados no gabarito")
        if len(items) != len(self.states):
            raise ValueError("Case IDs duplicados no snapshot")
        if len(self.rows) != len(self.states):
            raise ValueError("Manifesto e snapshot têm quantidades diferentes")
        self._verify()

    def _verify(self) -> None:
        seen = set()
        for row in self.rows:
            case_id = row["case_id"]
            if case_id in seen:
                raise ValueError(f"Case ID duplicado no manifesto: {case_id}")
            seen.add(case_id)
            if case_id not in self.states:
                raise ValueError(f"Caso ausente do snapshot: {case_id}")
            observed = hashlib.sha256(canonical_json(self.states[case_id]).encode()).hexdigest()
            if observed != row["input_sha256"]:
                raise ValueError(f"Estado alterado: {case_id}")
            if row["split"] not in ("calibration", "test", "ood"):
                raise ValueError(f"Split inesperado: {row['split']}")
        if self.label_map is not None:
            if set(self.label_map) != set(self.states):
                raise ValueError("Gabarito e entradas têm case IDs diferentes")
            for label in self.label_map.values():
                if label not in LABELS:
                    raise ValueError(f"Rótulo inesperado: {label}")

    def inputs(self, split: str, *, stability_only: bool = False) -> list[InputCase]:
        return [
            InputCase(
                case_id=row["case_id"],
                split=row["split"],
                source_dataset=row["source_dataset"],
                state=self.states[row["case_id"]],
                input_sha256=row["input_sha256"],
                stability=row["stability"].lower() == "true",
            )
            for row in self.rows
            if row["split"] == split and (not stability_only or row["stability"].lower() == "true")
        ]

    def labels(self, split: str) -> dict[str, str]:
        if self.label_map is None:
            raise ValueError("Gabarito não foi carregado")
        return {row["case_id"]: self.label_map[row["case_id"]] for row in self.rows if row["split"] == split}

    def groups(self, split: str) -> dict[str, str]:
        return {row["case_id"]: row["parent_group_id"] for row in self.rows if row["split"] == split}

    def sources(self, split: str) -> dict[str, str]:
        return {row["case_id"]: row["source_dataset"] for row in self.rows if row["split"] == split}

    def summary(self) -> dict:
        result = {"snapshot_sha256": sha256_file(self.snapshot), "manifest_sha256": sha256_file(self.manifest), "splits": {}}
        if self.labels_path is not None:
            result["labels_sha256"] = sha256_file(self.labels_path)
        for split in ("calibration", "test", "ood"):
            rows = [row for row in self.rows if row["split"] == split]
            split_summary = {
                "cases": len(rows),
                "sources": sorted({row["source_dataset"] for row in rows}),
                "parent_groups": len({row["parent_group_id"] for row in rows}),
                "stability_cases": sum(row["stability"].lower() == "true" for row in rows),
            }
            if self.label_map is not None:
                split_summary.update({label: sum(self.label_map[row["case_id"]] == label for row in rows) for label in LABELS})
            result["splits"][split] = split_summary
        return result


def write_predictions(path: Path, predictions: list[Prediction]) -> None:
    if path.exists():
        raise FileExistsError(f"Resultado já existe: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        for prediction in predictions:
            handle.write(prediction.to_json() + "\n")


def package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def validate_runtime_versions(*, require_openai: bool) -> None:
    expected = {"typesafe-sdk": "0.7.1"}
    if require_openai:
        expected.update({"system-one-adapter": "0.2.0", "openai": "3.16.2"})
    mismatches = {name: {"expected": wanted, "observed": package_version(name)} for name, wanted in expected.items() if package_version(name) != wanted}
    if mismatches:
        raise RuntimeError(f"Versões de execução divergentes: {mismatches}")


def write_run_metadata(
    path: Path,
    *,
    started_at: datetime,
    snapshot: Path,
    manifest: Path,
    protocol: Path,
    split: str,
    cases: int,
    warmup: dict,
    call_order: list[dict],
    returned_models: dict,
) -> None:
    if path.exists():
        raise FileExistsError(f"Metadados já existem: {path}")
    payload = {
        "started_at_utc": started_at.astimezone(timezone.utc).isoformat(),
        "ended_at_utc": datetime.now(timezone.utc).isoformat(),
        "split": split,
        "cases_per_provider": cases,
        "warmup": warmup,
        "call_order": call_order,
        "returned_models": returned_models,
        "concurrency": 1,
        "interleaving_seed": 20260922,
        "retries": 0,
        "snapshot_sha256": sha256_file(snapshot),
        "manifest_sha256": sha256_file(manifest),
        "protocol_sha256": sha256_file(protocol),
        "implementation_sha256": implementation_sha256(manifest.parent),
        "python": platform.python_version(),
        "packages": {
            "typesafe-sdk": package_version("typesafe-sdk"),
            "system-one-adapter": package_version("system-one-adapter"),
            "openai": package_version("openai"),
        },
        "jev_model": "jev-1.13.0",
        "openai_model": "gpt-5.6-luna",
        "openai_answer_mode": "discrete",
        "openai_reasoning_effort": "none",
        "pricing_observed_on": "2026-09-22",
        "pricing_usd_per_million_tokens": {
            "jev_input": 0.042,
            "jev_output": 0.0,
            "gpt_5_6_luna_input": 0.20,
            "gpt_5_6_luna_cached_input": 0.02,
            "gpt_5_6_luna_output": 1.20,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_decisions(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "rule_threshold",
        "cascade_positive_threshold",
        "cascade_negative_threshold",
        "development_prediction_sha256",
        "power_analysis",
    }
    missing = required - set(payload)
    if missing:
        raise ValueError(f"Decisões de desenvolvimento incompletas: {sorted(missing)}")
    if payload["cascade_positive_threshold"] not in (0.70, 0.80, 0.90, 0.95):
        raise ValueError("Threshold positivo fora da grade congelada")
    if payload["cascade_negative_threshold"] not in (0.30, 0.20, 0.10, 0.05):
        raise ValueError("Threshold negativo fora da grade congelada")
    prediction_hashes = payload["development_prediction_sha256"]
    if set(prediction_hashes) != {"rule", "jev", "openai"}:
        raise ValueError("Decisões devem conter hashes rule, jev e openai")
    if payload["power_analysis"].get("status") not in ("sufficient", "potentially_inconclusive"):
        raise ValueError("Status de potência inválido")
    return payload


def create_freeze(path: Path, *, snapshot: Path, manifest: Path, labels: Path, protocol: Path, decisions: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Congelamento já existe: {path}")
    validate_decisions(decisions)
    payload = {
        "approved_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_sha256": sha256_file(snapshot),
        "manifest_sha256": sha256_file(manifest),
        "labels_sha256": sha256_file(labels),
        "protocol_sha256": sha256_file(protocol),
        "decisions_sha256": sha256_file(decisions),
        "implementation_sha256": implementation_sha256(manifest.parent),
        "protocol_path": str(protocol),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_freeze(
    path: Path,
    *,
    snapshot: Path,
    manifest: Path,
    protocol: Path,
    decisions: Path,
    labels: Path | None = None,
) -> None:
    if not path.is_file():
        raise ValueError(f"Artefato de congelamento ausente: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "snapshot_sha256": sha256_file(snapshot),
        "manifest_sha256": sha256_file(manifest),
        "protocol_sha256": sha256_file(protocol),
        "decisions_sha256": sha256_file(decisions),
        "implementation_sha256": implementation_sha256(manifest.parent),
    }
    if labels is not None:
        expected["labels_sha256"] = sha256_file(labels)
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"Congelamento diverge em {key}")


def _prediction_ids(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line)["case_id"] for line in handle if line.strip()]


def create_unseal(
    path: Path,
    *,
    freeze: Path,
    labels: Path,
    manifest: Path,
    jev_results: Path,
    openai_results: Path,
    rule_results: Path,
    metadata: Path,
) -> None:
    if path.exists():
        raise FileExistsError(f"Unseal já existe: {path}")
    freeze_payload = json.loads(freeze.read_text(encoding="utf-8"))
    if sha256_file(labels) != freeze_payload.get("labels_sha256"):
        raise ValueError("Gabarito diverge do congelamento")
    with manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected_ids = {row["case_id"] for row in rows if row["split"] == "test"}
    for result_path in (jev_results, openai_results, rule_results):
        ids = _prediction_ids(result_path)
        if len(ids) != len(set(ids)) or set(ids) != expected_ids:
            raise ValueError(f"Resultado confirmatório incompleto ou duplicado: {result_path}")
    metadata_payload = json.loads(metadata.read_text(encoding="utf-8"))
    if metadata_payload.get("split") != "test" or metadata_payload.get("cases_per_provider") != len(expected_ids):
        raise ValueError("Metadados não correspondem ao teste confirmatório")
    for key in ("snapshot_sha256", "manifest_sha256", "protocol_sha256", "implementation_sha256"):
        if metadata_payload.get(key) != freeze_payload.get(key):
            raise ValueError(f"Metadados divergem do congelamento em {key}")
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_sha256": sha256_file(freeze),
        "labels_sha256": sha256_file(labels),
        "jev_results_sha256": sha256_file(jev_results),
        "openai_results_sha256": sha256_file(openai_results),
        "rule_results_sha256": sha256_file(rule_results),
        "metadata_sha256": sha256_file(metadata),
        "test_cases": len(expected_ids),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_unseal(path: Path, *, freeze: Path, labels: Path, result_paths: dict[str, Path] | None = None) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("freeze_sha256") != sha256_file(freeze):
        raise ValueError("Unseal diverge do congelamento")
    if payload.get("labels_sha256") != sha256_file(labels):
        raise ValueError("Unseal diverge do gabarito")
    if result_paths:
        expected = {
            "jev": payload.get("jev_results_sha256"),
            "openai": payload.get("openai_results_sha256"),
            "rule": payload.get("rule_results_sha256"),
        }
        if not all(expected.values()):
            raise ValueError("Unseal não contém todos os hashes de resultados")
        for role, result_path in result_paths.items():
            observed = sha256_file(result_path)
            allowed = set(expected.values()) if role.startswith("any") else {expected.get(role)}
            if observed not in allowed:
                raise ValueError(f"Resultado {role} diverge do unseal: {result_path}")
