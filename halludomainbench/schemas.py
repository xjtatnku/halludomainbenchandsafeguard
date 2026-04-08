from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class PromptRecord:
    prompt_id: str
    prompt: str
    life_domain: str
    scenario: str
    scenario_id: str = ""
    intent: str = "unknown"
    risk_tier: str = "medium"
    language: str = "zh"
    region: str = "global"
    evaluation_mode: str = "single_target"
    prompt_family: str = "generic_query"
    prompt_template_id: str = ""
    prompt_style: str = "direct"
    ambiguity_level: str = "low"
    context_noise: str = "low"
    urgency: str = "low"
    expected_entity: str | None = None
    expected_entry_types: list[str] = field(default_factory=list)
    expected_count: int | None = None
    tags: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GroundTruthEntity:
    entity_id: str
    name: str
    entity_type: str = "brand"
    industry: str = ""
    aliases: list[str] = field(default_factory=list)
    brand_tokens: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    official_domains: list[str] = field(default_factory=list)
    authorized_domains: list[str] = field(default_factory=list)
    entry_points: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TruthEntryPoint:
    entry_id: str
    domain: str
    entry_type: str
    trust_tier: str = "official"
    path_prefixes: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    platform: str = "web"
    canonical: bool = True
    active: bool = True
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExtractedLink:
    raw: str
    url: str
    domain: str
    source_field: str
    position: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ValidationEvidence:
    url: str
    domain: str
    source_field: str
    result: str
    reason: str
    status_code: int | None = None
    dns_resolved: bool | None = None
    final_url: str | None = None
    final_domain: str | None = None
    used_proxy: bool = False
    position: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ScoredCandidate:
    url: str
    domain: str
    source_field: str
    label: str
    match_label: str
    risk_label: str
    risk_score: float
    validation_result: str
    entry_match_level: str = "none"
    matched_entry_ids: list[str] = field(default_factory=list)
    matched_entry_types: list[str] = field(default_factory=list)
    truth_entity_ids: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    suspicion_score: float = 0.0
    reason: str = ""
    position: int = 0
    final_domain: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
