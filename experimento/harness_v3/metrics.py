from __future__ import annotations

import collections
import json
import math
import random
from pathlib import Path

from .core import LABELS


PRICES_PER_MILLION = {
    "deterministic": {"input": 0.0, "cached_input": 0.0, "output": 0.0},
    "typesafe": {"input": 0.042, "cached_input": 0.042, "output": 0.0},
    "openai": {"input": 0.20, "cached_input": 0.02, "output": 1.20},
}


def prediction_cost(item: dict) -> float | None:
    usage = item.get("usage") or {}
    if usage.get("estimated_cost_usd") is not None:
        return float(usage["estimated_cost_usd"])
    rates = PRICES_PER_MILLION.get(item.get("provider"))
    if rates is None:
        return None
    if item.get("provider") == "deterministic":
        return 0.0
    input_tokens = usage.get("input_tokens_total", usage.get("input_tokens"))
    output_tokens = usage.get("output_tokens_total", usage.get("output_tokens"))
    if input_tokens is None or output_tokens is None:
        return None
    cached = min(int(usage.get("cached_input_tokens") or 0), int(input_tokens))
    uncached = int(input_tokens) - cached
    return (uncached * rates["input"] + cached * rates["cached_input"] + int(output_tokens) * rates["output"]) / 1_000_000


def read_predictions(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def score(predictions: list[dict], labels: dict[str, str]) -> dict:
    by_id = {item["case_id"]: item for item in predictions}
    missing = set(labels) - set(by_id)
    extra = set(by_id) - set(labels)
    if missing or extra or len(by_id) != len(predictions):
        raise ValueError(f"Predições não correspondem ao split: missing={len(missing)} extra={len(extra)}")
    valid = [item for item in predictions if item["status"] == "ok" and item["label"] in LABELS]
    confusion = {expected: {predicted: 0 for predicted in LABELS} for expected in LABELS}
    for item in valid:
        confusion[labels[item["case_id"]]][item["label"]] += 1
    per_class = {}
    recalls = []
    f1s = []
    for label in LABELS:
        tp = confusion[label][label]
        fp = sum(confusion[other][label] for other in LABELS if other != label)
        support = sum(expected == label for expected in labels.values())
        fn = support - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
        recalls.append(recall)
        f1s.append(f1)
    negatives = sum(label == "NOT_ATTRIBUTABLE" for label in labels.values())
    valid_negatives = sum(labels[item["case_id"]] == "NOT_ATTRIBUTABLE" for item in valid)
    false_positives = confusion["NOT_ATTRIBUTABLE"]["ATTRIBUTABLE"]
    probabilistic = [item for item in valid if item.get("probability_attributable") is not None]
    brier = None
    ece = None
    if probabilistic:
        brier = sum((float(item["probability_attributable"]) - (labels[item["case_id"]] == "ATTRIBUTABLE")) ** 2 for item in probabilistic) / len(probabilistic)
        weighted_gap = 0.0
        for index in range(10):
            low, high = index / 10, (index + 1) / 10
            bucket = [item for item in probabilistic if low <= float(item["probability_attributable"]) < high or (index == 9 and float(item["probability_attributable"]) == 1.0)]
            if bucket:
                confidence = sum(float(item["probability_attributable"]) for item in bucket) / len(bucket)
                observed = sum(labels[item["case_id"]] == "ATTRIBUTABLE" for item in bucket) / len(bucket)
                weighted_gap += len(bucket) / len(probabilistic) * abs(confidence - observed)
        ece = weighted_gap
    risk_coverage = []
    if probabilistic:
        for threshold in (0.50, 0.60, 0.70, 0.80, 0.90, 0.95):
            decided = [item for item in probabilistic if max(float(item["probability_attributable"]), 1 - float(item["probability_attributable"])) >= threshold]
            decided_negatives = [item for item in decided if labels[item["case_id"]] == "NOT_ATTRIBUTABLE"]
            risk_coverage.append(
                {
                    "confidence_threshold": threshold,
                    "coverage": len(decided) / len(predictions) if predictions else 0.0,
                    "error_rate": sum(item["label"] != labels[item["case_id"]] for item in decided) / len(decided) if decided else None,
                    "false_attributable_rate_valid_decisions": (
                        sum(item["label"] == "ATTRIBUTABLE" for item in decided_negatives) / len(decided_negatives)
                        if decided_negatives
                        else None
                    ),
                }
            )
    prevalence_sensitivity = []
    true_positive_rate = per_class["ATTRIBUTABLE"]["recall"]
    false_positive_rate = false_positives / negatives if negatives else 0.0
    for attributable_prevalence in (0.10, 0.25, 0.50, 0.75, 0.90):
        numerator = true_positive_rate * attributable_prevalence
        denominator = numerator + false_positive_rate * (1 - attributable_prevalence)
        prevalence_sensitivity.append(
            {
                "hypothetical_attributable_prevalence": attributable_prevalence,
                "expected_precision_attributable": numerator / denominator if denominator else None,
            }
        )
    latencies = [float(item["latency_ms"]) for item in predictions]
    total_input_tokens = 0
    total_output_tokens = 0
    cost_usd = 0.0
    priced_cases = 0
    cached_input_tokens = 0
    for item in predictions:
        usage = item.get("usage") or {}
        components = usage.get("components")
        if components:
            usages = [value or {} for value in components.values()]
        else:
            usages = [usage]
        item_cost = prediction_cost(item)
        if item_cost is not None:
            priced_cases += 1
            cost_usd += item_cost
        for component_usage in usages:
            input_tokens = component_usage.get("input_tokens_total", component_usage.get("input_tokens"))
            output_tokens = component_usage.get("output_tokens_total", component_usage.get("output_tokens"))
            if input_tokens is not None:
                total_input_tokens += int(input_tokens)
            if output_tokens is not None:
                total_output_tokens += int(output_tokens)
            cached_input_tokens += int(component_usage.get("cached_input_tokens") or 0)
    return {
        "cases": len(predictions),
        "valid": len(valid),
        "operational_failures": len(predictions) - len(valid),
        "failure_rate": (len(predictions) - len(valid)) / len(predictions) if predictions else 0.0,
        "accuracy": sum(item["label"] == labels[item["case_id"]] for item in valid) / len(predictions) if predictions else 0.0,
        "balanced_accuracy": sum(recalls) / len(recalls),
        "macro_f1": sum(f1s) / len(f1s),
        "false_attributable_rate": false_positives / negatives if negatives else 0.0,
        "false_attributable_rate_valid_only": false_positives / valid_negatives if valid_negatives else 0.0,
        "per_class": per_class,
        "confusion": confusion,
        "brier": brier,
        "ece_10": ece,
        "risk_coverage": risk_coverage,
        "prevalence_sensitivity": prevalence_sensitivity,
        "latency_ms": {"p50": percentile(latencies, 0.5), "p95": percentile(latencies, 0.95)},
        "usage": {
            "input_tokens_observed": total_input_tokens,
            "cached_input_tokens_observed": cached_input_tokens,
            "output_tokens_observed": total_output_tokens,
            "priced_cases": priced_cases,
            "unpriced_cases": len(predictions) - priced_cases,
            "estimated_cost_lower_bound_usd": cost_usd,
            "estimated_cost_usd": cost_usd if priced_cases == len(predictions) else None,
            "estimated_cost_per_1000_usd": cost_usd * 1000 / len(predictions) if priced_cases == len(predictions) and predictions else None,
        },
    }


def cascade_predictions(jev: list[dict], llm: list[dict], positive_threshold: float, negative_threshold: float) -> list[dict]:
    by_llm = {item["case_id"]: item for item in llm}
    if {item["case_id"] for item in jev} != set(by_llm):
        raise ValueError("A cascata exige os mesmos casos")
    output = []
    for item in jev:
        probability = item.get("probability_attributable")
        use_jev = (
            item.get("status") == "ok"
            and probability is not None
            and (float(probability) >= positive_threshold or float(probability) <= negative_threshold)
        )
        selected = dict(item if use_jev else by_llm[item["case_id"]])
        if use_jev:
            selected["raw"] = {"cascade_route": "jev", "selected_raw": selected.get("raw")}
        else:
            llm_item = by_llm[item["case_id"]]
            jev_cost = prediction_cost(item)
            llm_cost = prediction_cost(llm_item)
            selected["provider"] = "cascade"
            selected["latency_ms"] = float(item["latency_ms"]) + float(llm_item["latency_ms"])
            selected["usage"] = {
                "estimated_cost_usd": jev_cost + llm_cost if jev_cost is not None and llm_cost is not None else None,
                "components": {"jev": item.get("usage"), "llm": llm_item.get("usage")},
            }
            selected["raw"] = {"cascade_route": "llm", "jev_raw": item.get("raw"), "llm_raw": llm_item.get("raw")}
        output.append(selected)
    return output


def select_cascade_threshold(jev: list[dict], llm: list[dict], labels: dict[str, str]) -> dict | None:
    llm_score = score(llm, labels)
    passing = []
    for positive_threshold in (0.70, 0.80, 0.90, 0.95):
        for negative_threshold in (0.30, 0.20, 0.10, 0.05):
            cascade = cascade_predictions(jev, llm, positive_threshold, negative_threshold)
            result = score(cascade, labels)
            coverage = sum(item["raw"]["cascade_route"] == "jev" for item in cascade) / len(cascade)
            if result["macro_f1"] >= llm_score["macro_f1"] - 0.01 and result["false_attributable_rate"] <= llm_score["false_attributable_rate"] + 0.01:
                passing.append((coverage, -result["false_attributable_rate"], positive_threshold, negative_threshold, result))
    if not passing:
        return None
    coverage, _, positive_threshold, negative_threshold, result = max(passing, key=lambda item: (item[0], item[1], item[2], -item[3]))
    return {
        "positive_threshold": positive_threshold,
        "negative_threshold": negative_threshold,
        "jev_coverage": coverage,
        "metrics": result,
        "llm_metrics": llm_score,
    }


def paired_bootstrap_difference(
    predictions_a: list[dict],
    predictions_b: list[dict],
    labels: dict[str, str],
    sources: dict[str, str],
    groups: dict[str, str],
    *,
    iterations: int = 10_000,
    seed: int = 20260922,
) -> dict:
    by_a = {item["case_id"]: item for item in predictions_a}
    by_b = {item["case_id"]: item for item in predictions_b}
    if set(by_a) != set(labels) or set(by_b) != set(labels):
        raise ValueError("A comparação pareada exige os mesmos casos completos")
    clusters_by_source: dict[str, dict[str, list[str]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    for case_id in labels:
        clusters_by_source[sources[case_id]][groups[case_id]].append(case_id)
    rng = random.Random(seed)
    samples = {"macro_f1": [], "false_attributable_rate": [], "failure_rate": []}
    for _ in range(iterations):
        selected = []
        for clusters in clusters_by_source.values():
            cluster_ids = sorted(clusters)
            for _ in cluster_ids:
                selected.extend(clusters[rng.choice(cluster_ids)])
        bootstrap_labels = {}
        bootstrap_a = []
        bootstrap_b = []
        for index, original_id in enumerate(selected):
            sample_id = f"{index}:{original_id}"
            bootstrap_labels[sample_id] = labels[original_id]
            for source, target in ((by_a, bootstrap_a), (by_b, bootstrap_b)):
                clone = dict(source[original_id])
                clone["case_id"] = sample_id
                target.append(clone)
        result_a = score(bootstrap_a, bootstrap_labels)
        result_b = score(bootstrap_b, bootstrap_labels)
        for metric in samples:
            samples[metric].append(result_a[metric] - result_b[metric])
    output = {}
    for metric, values in samples.items():
        values.sort()
        output[metric] = {
            "difference": score(predictions_a, labels)[metric] - score(predictions_b, labels)[metric],
            "bilateral_95_low": values[int(0.025 * iterations)],
            "bilateral_95_high": values[int(0.975 * iterations) - 1],
            "one_sided_95_low": values[int(0.05 * iterations)],
            "one_sided_95_high": values[int(0.95 * iterations) - 1],
        }
    return output


def _stability_rows(predictions: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = collections.defaultdict(list)
    for item in predictions:
        grouped[item["case_id"]].append(item)
    for case_id, rows in grouped.items():
        repeats = [(row.get("raw") or {}).get("stability_repeat") for row in rows]
        if len(rows) != 5 or set(repeats) != set(range(5)):
            raise ValueError(f"Estabilidade exige cinco chamadas distintas indexadas: {case_id}")
    return grouped


def stability(predictions: list[dict]) -> dict:
    grouped = _stability_rows(predictions)
    agreements = []
    ranges = []
    incomplete = 0
    for rows in grouped.values():
        valid = [row for row in rows if row["status"] == "ok"]
        if len(valid) != 5:
            incomplete += 1
            continue
        counts = collections.Counter(row["label"] for row in valid)
        agreements.append(max(counts.values()) / 5)
        values = [float(row["probability_attributable"]) for row in valid if row.get("probability_attributable") is not None]
        if len(values) == 5:
            ranges.append(max(values) - min(values))
    return {
        "cases": len(grouped),
        "incomplete_cases": incomplete,
        "mean_class_agreement": sum(agreements) / len(agreements) if agreements else None,
        "fully_stable_case_rate": sum(value == 1.0 for value in agreements) / len(agreements) if agreements else None,
        "probability_range_p50": percentile(ranges, 0.5),
        "probability_range_p95": percentile(ranges, 0.95),
    }


def stability_difference(jev: list[dict], llm: list[dict], *, iterations: int = 10_000, seed: int = 20260922) -> dict:
    def fully_stable_by_case(rows: list[dict]) -> dict[str, bool]:
        grouped = _stability_rows(rows)
        output = {}
        for case_id, case_rows in grouped.items():
            valid = [row for row in case_rows if row["status"] == "ok"]
            output[case_id] = len(valid) == 5 and len({row["label"] for row in valid}) == 1
        return output

    jev_values = fully_stable_by_case(jev)
    llm_values = fully_stable_by_case(llm)
    if set(jev_values) != set(llm_values):
        raise ValueError("Estabilidade pareada exige os mesmos casos")
    case_ids = sorted(jev_values)
    observed = sum(jev_values[case_id] - llm_values[case_id] for case_id in case_ids) / len(case_ids)
    rng = random.Random(seed)
    samples = []
    for _ in range(iterations):
        drawn = [rng.choice(case_ids) for _ in case_ids]
        samples.append(sum(jev_values[case_id] - llm_values[case_id] for case_id in drawn) / len(drawn))
    samples.sort()
    return {
        "cases": len(case_ids),
        "difference_fully_stable_rate": observed,
        "bilateral_95_low": samples[int(0.025 * iterations)],
        "bilateral_95_high": samples[int(0.975 * iterations) - 1],
        "one_sided_95_low": samples[int(0.05 * iterations)],
        "noninferiority_margin": -0.05,
        "passes": samples[int(0.05 * iterations)] >= -0.05,
    }
