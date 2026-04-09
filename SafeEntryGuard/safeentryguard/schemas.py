from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class EntryPoint:
    entry_id: str
    domain: str
    entry_type: str
    trust_tier: str = "official"
    path_prefixes: list[str] = field(default_factory=lambda: ["/"])


@dataclass(slots=True)
class Entity:
    entity_id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    brand_tokens: list[str] = field(default_factory=list)
    official_domains: list[str] = field(default_factory=list)
    authorized_domains: list[str] = field(default_factory=list)
    entry_points: list[EntryPoint] = field(default_factory=list)


@dataclass(slots=True)
class Candidate:
    raw_text: str
    normalized_url: str
    domain: str
    path: str
    scheme: str
    position: int


@dataclass(slots=True)
class EntityInference:
    entity_id: str
    confidence: float
    matched_terms: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MatchResult:
    entity_id: str = ""
    domain_label: str = "unknown"
    entry_match_level: str = "none"
    trust_tier: str = "none"
    matched_entry_types: list[str] = field(default_factory=list)
