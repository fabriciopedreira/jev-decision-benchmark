"""Audita a execução V4 antes de abrir o gabarito e calcula o placar pré-declarado."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


EXPERIMENT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(EXPERIMENT_ROOT))

from harness_v3.metrics import percentile, score
from harness_v4.runner import DatasetV4, LABELS, MANIFEST, sha256, verify_freeze


PRICES = {
    "jev": {"input": 0.042, "cached": 0.042, "output": 0.0},
    "luna": {"input": 0.20, "cached": 0.02, "output": 1.20},
    "terra": {"input": 2.00, "cached": 0.20, "output": 12.00},
}


def response_ids(prediction: dict) -> list[str]:
    raw = prediction.get("raw") or {}
    debug = raw.get("debug") or {}
    return [item["llm_response"]["id"] for item in debug.get("llm_attempts", [])
            if isinstance(item.get("llm_response"), dict) and item["llm_response"].get("id")]


def validate_and_unseal(results: Path, metadata: Path, freeze: Path, unseal_output: Path) -> tuple[list[dict], DatasetV4]:
    dataset = DatasetV4()
    verify_freeze(freeze, dataset)
    run_meta = json.loads(metadata.read_text(encoding="utf-8"))
    if run_meta.get("split") != "test" or run_meta.get("completed_cases") != 355:
        raise ValueError("Execução de teste incompleta")
    if run_meta.get("result_sha256") != sha256(results) or run_meta.get("freeze_sha256") != sha256(freeze):
        raise ValueError("Hash de resultado ou freeze divergente")
    rows = [json.loads(line) for line in results.open(encoding="utf-8") if line.strip()]
    expected = {case.case_id: case.input_sha256 for case in dataset.cases("test")}
    if len(rows) != len(expected) or len({row["case_id"] for row in rows}) != len(rows):
        raise ValueError("Casos faltantes ou repetidos")
    if {row["case_id"] for row in rows} != set(expected):
        raise ValueError("IDs de teste divergentes")
    seen_openai_ids = set()
    for row in rows:
        if row["input_sha256"] != expected[row["case_id"]]:
            raise ValueError(f"Estado divergente: {row['case_id']}")
        if set(row["block_order"]) != {"luna_baseline", "terra_baseline", "cascade"}:
            raise ValueError(f"Blocos incompletos: {row['case_id']}")
        for condition, wanted in (("luna_baseline", "gpt-5.6-luna"), ("terra_baseline", "gpt-5.6-terra")):
            pred = row[condition]
            if pred["status"] == "ok" and pred["label"] not in ("ATTRIBUTABLE", "NOT_ATTRIBUTABLE"):
                raise ValueError(f"Classe inválida: {row['case_id']} {condition}")
            if pred["status"] == "ok" and pred["model"] != wanted:
                raise ValueError(f"Modelo retornado inesperado: {row['case_id']} {condition}")
            ids = response_ids(pred)
            if pred["status"] == "ok" and not ids:
                raise ValueError(f"ID OpenAI ausente: {row['case_id']} {condition}")
            if seen_openai_ids.intersection(ids):
                raise ValueError(f"Resposta OpenAI reutilizada: {row['case_id']}")
            seen_openai_ids.update(ids)
        cascade = row["cascade"]
        jev = cascade["jev"]
        if jev["status"] == "ok" and (jev["label"] not in ("ATTRIBUTABLE", "NOT_ATTRIBUTABLE") or not 0 <= float(jev["probability_attributable"]) <= 1):
            raise ValueError(f"Resposta Jev inválida: {row['case_id']}")
        if jev["status"] == "ok" and jev["model"] != "jev-1.13.0":
            raise ValueError(f"Modelo Jev retornado inesperado: {row['case_id']}")
        probability = jev.get("probability_attributable")
        expected_route = "jev" if jev["status"] == "ok" and probability is not None and (probability <= 0.30 or probability >= 0.70) else "luna_after_jev"
        if cascade["route"] != expected_route:
            raise ValueError(f"Rota divergiu da política: {row['case_id']}")
        if expected_route == "jev" and cascade["luna"] is not None:
            raise ValueError(f"Chamada Luna indevida: {row['case_id']}")
        if expected_route != "jev":
            if cascade["luna"] is None:
                raise ValueError(f"Chamada Luna ausente: {row['case_id']}")
            baseline_ids = response_ids(row["luna_baseline"])
            cascade_ids = response_ids(cascade["luna"])
            if row["luna_baseline"]["status"] == "ok" and not baseline_ids:
                raise ValueError(f"ID da baseline Luna ausente: {row['case_id']}")
            if cascade["luna"]["status"] == "ok" and not cascade_ids:
                raise ValueError(f"ID da Luna na cascata ausente: {row['case_id']}")
            if cascade["luna"]["status"] == "ok" and cascade["luna"]["model"] != "gpt-5.6-luna":
                raise ValueError(f"Modelo Luna da cascata inesperado: {row['case_id']}")
            if set(baseline_ids) & set(cascade_ids) or seen_openai_ids.intersection(cascade_ids):
                raise ValueError(f"Resposta Luna reutilizada: {row['case_id']}")
            seen_openai_ids.update(cascade_ids)
        selected = jev if expected_route == "jev" else cascade["luna"]
        if cascade["final_label"] != (selected["label"] if selected["status"] == "ok" else None):
            raise ValueError(f"Classe final incorreta: {row['case_id']}")
        if cascade["latency_ms"] + 1e-6 < jev["latency_ms"]:
            raise ValueError(f"Latência composta menor que a primeira perna: {row['case_id']}")
        if cascade["luna"] is not None and cascade["latency_ms"] + 5 < jev["latency_ms"] + cascade["luna"]["latency_ms"]:
            raise ValueError(f"Latência composta não inclui duas pernas: {row['case_id']}")
    if unseal_output.exists():
        raise FileExistsError("Arquivo de abertura já existe")
    record = {
        "opened_at_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_sha256": sha256(freeze),
        "results_sha256": sha256(results),
        "metadata_sha256": sha256(metadata),
        "labels_sha256": sha256(LABELS),
        "analysis_sha256": sha256(Path(__file__)),
        "complete_distinct_cases": len(rows),
        "routed_luna_calls_distinct_from_baseline": sum(row["cascade"]["route"] == "luna_after_jev" for row in rows),
    }
    with unseal_output.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return rows, dataset


def test_labels() -> tuple[dict[str, str], dict[str, str]]:
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["case_id"]: row for row in csv.DictReader(handle) if row["split"] == "test"}
    with LABELS.open(newline="", encoding="utf-8") as handle:
        records = [row for row in csv.DictReader(handle) if row["case_id"] in manifest]
    labels = {row["case_id"]: row["published_label"] for row in records}
    originals = {row["case_id"]: row["original_label"] for row in records}
    if len(labels) != len(manifest) or len(originals) != len(manifest):
        raise ValueError("Gabarito incompleto")
    return labels, originals


def cost(prediction: dict, model: str) -> float | None:
    usage = prediction.get("usage") or {}
    input_tokens = usage.get("input_tokens_total", usage.get("input_tokens"))
    output_tokens = usage.get("output_tokens_total", usage.get("output_tokens"))
    if input_tokens is None or output_tokens is None:
        return None
    cached = min(int(usage.get("cached_input_tokens") or 0), int(input_tokens))
    cache_write = 0
    if model != "jev":
        raw = prediction.get("raw") or {}
        debug = raw.get("debug") or {}
        for attempt in debug.get("llm_attempts", []):
            response = attempt.get("llm_response") or {}
            details = (response.get("usage") or {}).get("input_tokens_details") or {}
            cache_write += int(details.get("cache_write_tokens") or 0)
        if cached + cache_write > int(input_tokens):
            raise ValueError("Tokens de cache excedem o total de entrada")
    rates = PRICES[model]
    regular = int(input_tokens) - cached - cache_write
    return (regular * rates["input"] + cache_write * rates["input"] * 1.25 + cached * rates["cached"] + int(output_tokens) * rates["output"]) / 1_000_000


def condition_predictions(rows: list[dict]) -> dict[str, list[dict]]:
    output = {name: [] for name in ("rule", "jev", "luna", "terra", "cascade")}
    for row in rows:
        output["rule"].append(row["rule"])
        output["jev"].append(row["cascade"]["jev"])
        output["luna"].append(row["luna_baseline"])
        output["terra"].append(row["terra_baseline"])
        cascade = row["cascade"]
        output["cascade"].append({
            "case_id": row["case_id"],
            "provider": "cascade",
            "model": "jev-1.13.0->gpt-5.6-luna",
            "label": cascade["final_label"],
            "probability_attributable": None,
            "latency_ms": cascade["latency_ms"],
            "status": cascade["status"],
            "usage": None,
        })
    return output


def short_score(predictions: dict[str, dict], labels: dict[str, str], ids: list[str]) -> tuple[float, float, float]:
    tp = tn = fp = fn = failures = 0
    for case_id in ids:
        item = predictions[case_id]
        truth = labels[case_id]
        pred = item["label"] if item["status"] == "ok" else None
        if pred is None:
            failures += 1
        elif truth == "ATTRIBUTABLE" and pred == "ATTRIBUTABLE":
            tp += 1
        elif truth == "NOT_ATTRIBUTABLE" and pred == "NOT_ATTRIBUTABLE":
            tn += 1
        elif truth == "NOT_ATTRIBUTABLE":
            fp += 1
        else:
            fn += 1
    positive = sum(labels[case_id] == "ATTRIBUTABLE" for case_id in ids)
    negative = sum(labels[case_id] == "NOT_ATTRIBUTABLE" for case_id in ids)
    f1_positive = 2 * tp / (2 * tp + fp + positive - tp) if 2 * tp + fp + positive - tp else 0.0
    f1_negative = 2 * tn / (2 * tn + fn + negative - tn) if 2 * tn + fn + negative - tn else 0.0
    return (f1_positive + f1_negative) / 2, fp / negative if negative else 0.0, failures / len(ids)


def bootstrap_differences(conditions: dict[str, list[dict]], labels: dict[str, str], groups: dict[str, str]) -> dict:
    by_condition = {name: {row["case_id"]: row for row in rows} for name, rows in conditions.items()}
    clusters = defaultdict(list)
    for case_id in labels:
        clusters[groups[case_id]].append(case_id)
    group_ids = sorted(clusters)
    contrasts = (("jev", "luna"), ("jev", "terra"), ("cascade", "luna"), ("cascade", "terra"),
                 ("rule", "jev"), ("rule", "luna"), ("rule", "terra"), ("rule", "cascade"))
    samples = {f"{a}_minus_{b}": {"macro_f1": [], "false_attributable_rate": [], "failure_rate": []} for a, b in contrasts}
    rng = random.Random(20260923)
    for _ in range(10_000):
        selected = [case_id for _ in group_ids for case_id in clusters[rng.choice(group_ids)]]
        scores = {name: short_score(predictions, labels, selected) for name, predictions in by_condition.items()}
        for a, b in contrasts:
            key = f"{a}_minus_{b}"
            for index, metric in enumerate(("macro_f1", "false_attributable_rate", "failure_rate")):
                samples[key][metric].append(scores[a][index] - scores[b][index])
    final = {}
    all_ids = list(labels)
    point = {name: short_score(predictions, labels, all_ids) for name, predictions in by_condition.items()}
    for a, b in contrasts:
        key = f"{a}_minus_{b}"
        final[key] = {}
        for index, metric in enumerate(("macro_f1", "false_attributable_rate", "failure_rate")):
            values = sorted(samples[key][metric])
            final[key][metric] = {
                "difference": point[a][index] - point[b][index],
                "bilateral_95": [values[250], values[9749]],
                "one_sided_95_low": values[500],
                "one_sided_95_high": values[9499],
            }
    return final


def margin_state(interval: dict, margin: float, *, higher_is_better: bool) -> str:
    if higher_is_better:
        if interval["one_sided_95_low"] >= margin:
            return "pass"
        if interval["one_sided_95_high"] < margin:
            return "fail"
    else:
        if interval["one_sided_95_high"] <= margin:
            return "pass"
        if interval["one_sided_95_low"] > margin:
            return "fail"
    return "inconclusive"


def combine_states(*states: str) -> str:
    if "fail" in states:
        return "fail"
    if all(state == "pass" for state in states):
        return "pass"
    return "inconclusive"


def analyze(rows: list[dict], labels: dict[str, str], originals: dict[str, str]) -> dict:
    conditions = condition_predictions(rows)
    metrics = {name: score(predictions, labels) for name, predictions in conditions.items()}
    for values in metrics.values():
        # score() da V3 tem tarifa OpenAI única (Luna); a V4 precifica Terra abaixo.
        values.pop("usage", None)
    for name in ("luna", "terra", "cascade", "rule"):
        metrics[name]["brier"] = None
        metrics[name]["ece_10"] = None
        metrics[name]["risk_coverage"] = []
    costs = {}
    for name in ("jev", "luna", "terra", "cascade"):
        values = []
        tokens = Counter()
        for row in rows:
            if name == "jev":
                components = [(row["cascade"]["jev"], "jev")]
            elif name == "luna":
                components = [(row["luna_baseline"], "luna")]
            elif name == "terra":
                components = [(row["terra_baseline"], "terra")]
            else:
                components = [(row["cascade"]["jev"], "jev")]
                if row["cascade"]["luna"] is not None:
                    components.append((row["cascade"]["luna"], "luna"))
            component_values = [cost(prediction, model) for prediction, model in components]
            for prediction, _ in components:
                usage = prediction.get("usage") or {}
                tokens["input"] += int(usage.get("input_tokens_total", usage.get("input_tokens")) or 0)
                tokens["cached_input"] += int(usage.get("cached_input_tokens") or 0)
                tokens["output"] += int(usage.get("output_tokens_total", usage.get("output_tokens")) or 0)
                raw = prediction.get("raw") or {}
                for attempt in (raw.get("debug") or {}).get("llm_attempts", []):
                    response = attempt.get("llm_response") or {}
                    details = (response.get("usage") or {}).get("input_tokens_details") or {}
                    tokens["cache_write"] += int(details.get("cache_write_tokens") or 0)
            values.append(sum(component_values) if all(value is not None for value in component_values) else None)
        known = [value for value in values if value is not None]
        costs[name] = {
            "priced_cases": len(known),
            "unpriced_cases": len(values) - len(known),
            "observed_lower_bound_usd": sum(known),
            "calculated_total_usd": sum(known) if len(known) == len(values) else None,
            "calculated_per_1000_usd": sum(known) * 1000 / len(values) if len(known) == len(values) else None,
            "tokens_observed": dict(tokens),
        }
    groups = {}
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["split"] == "test":
                groups[row["case_id"]] = row["parent_group_id"]
    differences = bootstrap_differences(conditions, labels, groups)
    coverage = sum(row["cascade"]["route"] == "jev" for row in rows) / len(rows)
    luna_cost = costs["luna"]["calculated_total_usd"]
    cascade_cost = costs["cascade"]["calculated_total_usd"]
    savings = 1 - cascade_cost / luna_cost if luna_cost and cascade_cost is not None else None
    cascade_quality = differences["cascade_minus_luna"]
    direct_quality = differences["jev_minus_luna"]
    code_contrasts = [differences[f"rule_minus_{name}"] for name in ("jev", "luna", "terra", "cascade")]
    code_state = combine_states(*[
        margin_state(item[metric], margin, higher_is_better=higher)
        for item in code_contrasts
        for metric, margin, higher in (("macro_f1", -0.03, True), ("false_attributable_rate", 0.02, False))
    ])
    jev_cost = costs["jev"]["calculated_total_usd"]
    direct_cost_ratio = luna_cost / jev_cost if jev_cost and luna_cost is not None else None
    direct_p95_ratio = metrics["luna"]["latency_ms"]["p95"] / metrics["jev"]["latency_ms"]["p95"]
    direct_failure_state = margin_state(direct_quality["failure_rate"], 0.005, higher_is_better=False)
    direct_system_state = combine_states(
        "pass" if direct_cost_ratio is not None and direct_cost_ratio >= 5 else "fail" if direct_cost_ratio is not None else "inconclusive",
        "pass" if direct_p95_ratio >= 2 else "fail",
        direct_failure_state,
    )
    direct_quality_state = combine_states(
        margin_state(direct_quality["macro_f1"], -0.03, higher_is_better=True),
        margin_state(direct_quality["false_attributable_rate"], 0.02, higher_is_better=False),
    )
    cascade_state = combine_states(
        "pass" if coverage >= 0.25 else "fail",
        "pass" if savings is not None and savings >= 0.30 else "fail" if savings is not None else "inconclusive",
        margin_state(cascade_quality["macro_f1"], -0.01, higher_is_better=True),
        margin_state(cascade_quality["false_attributable_rate"], 0.01, higher_is_better=False),
    )
    by_original = {}
    for original in ("supported", "partially_supported", "not_supported"):
        ids = [case_id for case_id, value in originals.items() if value == original]
        by_original[original] = {
            name: {"cases": len(ids), "correct": sum(predictions[case_id]["status"] == "ok" and predictions[case_id]["label"] == labels[case_id] for case_id in ids),
                   "false_attributable": sum(labels[case_id] == "NOT_ATTRIBUTABLE" and predictions[case_id]["status"] == "ok" and predictions[case_id]["label"] == "ATTRIBUTABLE" for case_id in ids)}
            for name, predictions in ((name, {row["case_id"]: row for row in values}) for name, values in conditions.items())
        }
    return {
        "cases": len(rows),
        "groups": len(set(groups.values())),
        "label_counts": dict(Counter(labels.values())),
        "routes": dict(Counter(row["cascade"]["route"] for row in rows)),
        "metrics": metrics,
        "costs": costs,
        "paired_group_bootstrap": differences,
        "preregistered_gate_readout": {
            "code_within_margins_of_all_model_conditions": code_state,
            "jev_direct_quality_vs_luna": direct_quality_state,
            "jev_direct_cost_ratio_vs_luna": direct_cost_ratio,
            "jev_direct_p95_ratio_vs_luna": direct_p95_ratio,
            "jev_direct_failure_margin_vs_luna": direct_failure_state,
            "jev_direct_system_vs_luna_excluding_stability": direct_system_state,
            "jev_direct_overall": "not_evaluable_without_v4_stability",
            "cascade_coverage": coverage,
            "cascade_calculated_savings_vs_luna": savings,
            "cascade_technical_gates_vs_luna": cascade_state,
            "publication_or_automation_authorized": False,
        },
        "original_label_breakdown": by_original,
        "pricing_sources": {
            "jev": "https://typesafe.ai/blog/introducing-system-one-models-and-jev",
            "luna": "https://developers.openai.com/api/docs/models/gpt-5.6-luna",
            "terra": "https://developers.openai.com/api/docs/models/gpt-5.6-terra",
        },
        "pricing_observed_on": "2026-09-23",
        "cost_note": "Cálculo a partir dos tokens reportados e preços publicados; não é fatura.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--unseal-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Análise já existe; não sobrescrever")
    rows, _ = validate_and_unseal(args.results, args.metadata, args.freeze, args.unseal_output)
    labels, originals = test_labels()
    result = analyze(rows, labels, originals)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"status": "analyzed", "cases": result["cases"], "groups": result["groups"]}))


if __name__ == "__main__":
    main()
