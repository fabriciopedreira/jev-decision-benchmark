from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version


LABELS = ("ATTRIBUTABLE", "NOT_ATTRIBUTABLE")


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
