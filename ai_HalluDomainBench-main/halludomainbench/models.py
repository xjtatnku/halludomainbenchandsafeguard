from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .utils import read_json, resolve_path


@dataclass(slots=True)
class ModelSpec:
    model_id: str
    provider: str = "siliconflow"
    label: str = ""
    family: str = ""
    tags: list[str] = field(default_factory=list)
    enabled: bool = True
    request_overrides: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ModelRegistry:
    path: Path | None
    models_by_id: dict[str, ModelSpec]
    lineups: dict[str, list[str]]
    metadata: dict[str, Any] = field(default_factory=dict)

    def select(
        self,
        *,
        lineup: str = "",
        include_tags: set[str] | None = None,
        limit: int = 0,
        include_disabled: bool = False,
    ) -> list[ModelSpec]:
        include_tags = include_tags or set()
        if lineup:
            if lineup not in self.lineups:
                raise ValueError(f"Unknown model lineup: {lineup}")
            model_ids = self.lineups[lineup]
        else:
            model_ids = list(self.models_by_id.keys())

        selected: list[ModelSpec] = []
        for model_id in model_ids:
            spec = self.models_by_id.get(model_id)
            if spec is None:
                raise ValueError(f"Lineup references unknown model: {model_id}")
            if not include_disabled and not spec.enabled:
                continue
            if include_tags and not include_tags.issubset(set(spec.tags)):
                continue
            selected.append(spec)
            if limit > 0 and len(selected) >= limit:
                break
        return selected


def normalize_model_spec(payload: str | dict[str, Any] | ModelSpec) -> ModelSpec:
    if isinstance(payload, ModelSpec):
        return payload
    if isinstance(payload, str):
        return ModelSpec(model_id=payload, label=payload)
    if not isinstance(payload, dict):
        raise TypeError(f"Unsupported model spec payload: {type(payload)!r}")

    model_id = str(payload.get("model_id") or payload.get("model") or payload.get("name") or "").strip()
    if not model_id:
        raise ValueError(f"Model spec is missing model_id/name: {payload!r}")

    metadata = {
        key: value
        for key, value in payload.items()
        if key
        not in {
            "model_id",
            "model",
            "name",
            "provider",
            "label",
            "family",
            "tags",
            "enabled",
            "request_overrides",
        }
    }

    return ModelSpec(
        model_id=model_id,
        provider=str(payload.get("provider") or "siliconflow").strip() or "siliconflow",
        label=str(payload.get("label") or model_id).strip() or model_id,
        family=str(payload.get("family") or "").strip(),
        tags=[str(tag).strip() for tag in payload.get("tags", []) if str(tag).strip()],
        enabled=bool(payload.get("enabled", True)),
        request_overrides=dict(payload.get("request_overrides") or {}),
        metadata=metadata,
    )


def _legacy_lineups(payload: dict[str, Any]) -> dict[str, list[str]]:
    lineups: dict[str, list[str]] = {}
    for key, value in payload.items():
        if key in {"models", "lineups", "paired_ablations", "version", "provider"}:
            continue
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            lineups[key] = list(value)

    paired = payload.get("paired_ablations")
    if isinstance(paired, dict):
        for key, value in paired.items():
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                lineups[key] = list(value)
                lineups[f"paired_ablations.{key}"] = list(value)
    return lineups


def load_model_registry(path: Path) -> ModelRegistry:
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Model registry must be a JSON object: {path}")

    models: dict[str, ModelSpec] = {}
    for item in payload.get("models", []):
        spec = normalize_model_spec(item)
        models[spec.model_id] = spec

    lineups = payload.get("lineups")
    if not isinstance(lineups, dict):
        lineups = _legacy_lineups(payload)

    if not models:
        for model_ids in lineups.values():
            for model_id in model_ids:
                if model_id not in models:
                    models[model_id] = normalize_model_spec(model_id)

    return ModelRegistry(
        path=path,
        models_by_id=models,
        lineups={key: list(value) for key, value in lineups.items()},
        metadata={
            key: value
            for key, value in payload.items()
            if key not in {"models", "lineups", "paired_ablations"}
        },
    )


def resolve_model_selection(
    *,
    root_dir: Path,
    models_payload: list[str] | list[dict[str, Any]] | None,
    registry_path: str | Path | None = None,
    selection: dict[str, Any] | None = None,
) -> tuple[list[str], list[ModelSpec], Path | None, str]:
    selection = selection or {}
    registry_file: Path | None = None

    if registry_path:
        registry_file = resolve_path(root_dir, registry_path)
        registry = load_model_registry(registry_file)
        specs = registry.select(
            lineup=str(selection.get("lineup") or "").strip(),
            include_tags={str(tag).strip() for tag in selection.get("include_tags", []) if str(tag).strip()},
            limit=int(selection.get("limit") or 0),
            include_disabled=bool(selection.get("include_disabled", False)),
        )
        if specs:
            return [spec.model_id for spec in specs], specs, registry_file, str(selection.get("lineup") or "")

    specs = [normalize_model_spec(item) for item in (models_payload or [])]
    specs = [spec for spec in specs if spec.enabled]
    return [spec.model_id for spec in specs], specs, registry_file, ""
