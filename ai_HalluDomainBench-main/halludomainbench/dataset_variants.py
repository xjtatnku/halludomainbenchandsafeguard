from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import read_json, write_json


def derive_dataset_subset(
    input_path: Path,
    output_path: Path,
    *,
    dataset_name: str,
    dataset_version: str,
    evaluation_modes: set[str] | None = None,
    intents: set[str] | None = None,
    require_expected_entity: bool = False,
) -> dict[str, Any]:
    payload = read_json(input_path)
    if not isinstance(payload, dict):
        raise ValueError(f"Dataset bundle must be a JSON object with records: {input_path}")

    records = list(payload.get("records") or [])
    filtered: list[dict[str, Any]] = []
    for record in records:
        if evaluation_modes and str(record.get("evaluation_mode", "")) not in evaluation_modes:
            continue
        if intents and str(record.get("intent", "")) not in intents:
            continue
        if require_expected_entity and not record.get("expected_entity"):
            continue
        filtered.append(record)

    bundle = {
        "dataset_name": dataset_name,
        "dataset_version": dataset_version,
        "region": payload.get("region", "global"),
        "records": filtered,
        "metadata": {
            **dict(payload.get("metadata") or {}),
            "source_dataset_name": payload.get("dataset_name", ""),
            "source_dataset_version": payload.get("dataset_version", ""),
            "subset_filters": {
                "evaluation_modes": sorted(evaluation_modes) if evaluation_modes else [],
                "intents": sorted(intents) if intents else [],
                "require_expected_entity": require_expected_entity,
            },
            "record_count": len(filtered),
        },
    }
    write_json(output_path, bundle)
    return bundle


def deduplicate_dataset(
    input_path: Path,
    output_path: Path,
    *,
    dedup_key: str = "prompt",
) -> dict[str, Any]:
    payload = read_json(input_path)
    bundle_mode = isinstance(payload, dict)
    if bundle_mode:
        records_key = "records" if isinstance(payload.get("records"), list) else "prompts"
        records = list(payload.get(records_key) or [])
    elif isinstance(payload, list):
        records_key = ""
        records = list(payload)
    else:
        raise ValueError(f"Dataset must be a JSON list or bundle object: {input_path}")

    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    dropped = 0
    for record in records:
        value = str(record.get(dedup_key, "") or "").strip()
        identity = value or f"__empty__:{len(deduped) + dropped}"
        if identity in seen:
            dropped += 1
            continue
        seen.add(identity)
        deduped.append(record)

    if bundle_mode:
        bundle = dict(payload)
        bundle[records_key] = deduped
        metadata = dict(bundle.get("metadata") or {})
        metadata["dedup"] = {
            "source_path": str(input_path),
            "dedup_key": dedup_key,
            "input_count": len(records),
            "output_count": len(deduped),
            "removed_count": dropped,
        }
        bundle["metadata"] = metadata
        write_json(output_path, bundle)
    else:
        write_json(output_path, deduped)

    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "dedup_key": dedup_key,
        "input_count": len(records),
        "output_count": len(deduped),
        "removed_count": dropped,
    }
