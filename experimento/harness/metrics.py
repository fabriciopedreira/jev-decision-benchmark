from __future__ import annotations

import math
from .core import LABELS


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
    }
