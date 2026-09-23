"""Prepara WiCE claim-level sem expor rótulos aos julgadores.

Execute com --output-dir em uma pasta vazia. Nenhuma API de modelo é chamada.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import urllib.request
from collections import Counter
from pathlib import Path


COMMIT = "ddeb6c183665e2a20c5f03c5aa07f03888b9870f"
BASE_URL = f"https://raw.githubusercontent.com/ryokamoi/wice/{COMMIT}/data/entailment_retrieval/claim"
MAX_EVIDENCE_CHARS = 60_000
LABEL_MAP = {
    "supported": "ATTRIBUTABLE",
    "partially_supported": "NOT_ATTRIBUTABLE",
    "not_supported": "NOT_ATTRIBUTABLE",
}


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def download(split: str) -> tuple[list[dict], str, str]:
    if split not in ("dev", "test"):
        raise ValueError(f"Split não permitido: {split}")
    url = f"{BASE_URL}/{split}.jsonl"
    with urllib.request.urlopen(url, timeout=60) as response:
        raw = response.read()
    records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    return records, hashlib.sha256(raw).hexdigest(), url


def prepare_records(records: list[dict], split: str) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    if split not in ("calibration", "test"):
        raise ValueError(f"Split não permitido: {split}")
    states: list[dict] = []
    manifest: list[dict] = []
    labels: list[dict] = []
    exclusions: list[dict] = []
    seen_ids: set[str] = set()
    for row in records:
        meta = row["meta"]
        case_id = "wice:" + str(meta["id"])
        if case_id in seen_ids:
            raise ValueError(f"ID duplicado: {case_id}")
        seen_ids.add(case_id)
        claim = row["claim"]
        evidence = row["evidence"]
        context = meta.get("claim_context", "")
        if not isinstance(claim, str) or not isinstance(evidence, list) or not all(isinstance(part, str) for part in evidence):
            raise ValueError(f"Formato inesperado: {case_id}")
        if not isinstance(context, str):
            raise ValueError(f"Contexto inesperado: {case_id}")
        if row["label"] not in LABEL_MAP:
            raise ValueError(f"Rótulo inesperado: {case_id}")
        reason = None
        if not claim.strip():
            reason = "empty_claim"
        elif not any(part.strip() for part in evidence):
            reason = "empty_evidence"
        elif sum(map(len, evidence)) > MAX_EVIDENCE_CHARS:
            reason = "evidence_over_60000_chars"
        if reason:
            exclusions.append({"case_id": case_id, "reason": reason})
            continue
        state = {"claim": claim, "claim_context": context, "evidence": evidence}
        title = str(meta["claim_title"]).strip()
        if not title:
            raise ValueError(f"Título vazio: {case_id}")
        group_hash = hashlib.sha256(title.encode("utf-8")).hexdigest()
        states.append({"case_id": case_id, "state": state})
        manifest.append({
            "case_id": case_id,
            "split": split,
            "source_dataset": "WiCE-claim",
            "parent_group_id": group_hash,
            "input_sha256": hashlib.sha256(canonical_json(state).encode("utf-8")).hexdigest(),
        })
        labels.append({"case_id": case_id, "published_label": LABEL_MAP[row["label"]], "original_label": row["label"]})
    return states, manifest, labels, exclusions


def csv_text(rows: list[dict], fields: list[str]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def build(output_dir: Path) -> dict:
    all_states: list[dict] = []
    all_manifest: list[dict] = []
    all_labels: list[dict] = []
    all_exclusions: list[dict] = []
    origins = {}
    for source_split, target_split in (("dev", "calibration"), ("test", "test")):
        records, sha256, url = download(source_split)
        states, manifest, labels, exclusions = prepare_records(records, target_split)
        all_states.extend(states)
        all_manifest.extend(manifest)
        all_labels.extend(labels)
        all_exclusions.extend(exclusions)
        origins[source_split] = {"url": url, "sha256": sha256, "raw_cases": len(records)}
    ids = [row["case_id"] for row in all_manifest]
    if len(ids) != len(set(ids)):
        raise ValueError("IDs repetidos entre splits")
    split_groups = {
        split: {row["parent_group_id"] for row in all_manifest if row["split"] == split}
        for split in ("calibration", "test")
    }
    if split_groups["calibration"] & split_groups["test"]:
        raise ValueError("Página de origem vazou entre splits")
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "snapshot": output_dir / "entradas.jsonl",
        "manifest": output_dir / "manifesto.csv",
        "labels": output_dir / "gabarito.csv",
        "audit": output_dir / "auditoria.json",
    }
    if any(path.exists() for path in paths.values()):
        raise FileExistsError("Ao menos um artefato já existe; não sobrescrever")
    texts = {
        "snapshot": "".join(canonical_json(row) + "\n" for row in all_states),
        "manifest": csv_text(all_manifest, ["case_id", "split", "source_dataset", "parent_group_id", "input_sha256"]),
        "labels": csv_text(all_labels, ["case_id", "published_label", "original_label"]),
    }
    audit = {
        "source_commit": COMMIT,
        "origins": origins,
        "max_evidence_chars": MAX_EVIDENCE_CHARS,
        "raw_cases": sum(item["raw_cases"] for item in origins.values()),
        "kept_cases": len(all_states),
        "exclusions": all_exclusions,
        "split_counts": dict(Counter(row["split"] for row in all_manifest)),
        "split_groups": {split: len(groups) for split, groups in split_groups.items()},
        "artifact_sha256": {name: hashlib.sha256(content.encode("utf-8")).hexdigest() for name, content in texts.items()},
    }
    texts["audit"] = json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    for name, path in paths.items():
        with path.open("x", encoding="utf-8") as handle:
            handle.write(texts[name])
    return {"paths": {name: str(path) for name, path in paths.items()}, "audit": audit}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
