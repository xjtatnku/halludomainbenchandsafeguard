from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from .schemas import GroundTruthEntity, PromptRecord, TruthEntryPoint
from .utils import read_json, write_json


COMMON_SUBDOMAINS = {
    "www",
    "m",
    "mobile",
    "app",
    "open",
    "api",
    "docs",
    "developer",
    "help",
    "support",
    "login",
    "account",
    "auth",
}
ENTITY_SUFFIXES = (
    "的官方网站",
    "官方网站",
    "官方网站",
    "的官网地址",
    "官网地址",
    "官网登录入口",
    "的官网登录入口",
    "官网登录页",
    "的登录页面",
    "登录页面",
    "的登录入口",
    "登录入口",
    "的网上银行",
    "网上银行",
    "的下载地址",
    "下载地址",
    "的下载页",
    "下载页",
    "的下载",
    "电脑版登录",
    "的登录",
    "的官网",
    "官方网站",
    "官网",
    "登录",
    "下载",
    "页面",
    "入口",
)


def normalize_domain(domain: str) -> str:
    return domain.lower().strip().rstrip(".")


def normalize_path(path: str) -> str:
    clean = (path or "/").strip()
    if not clean:
        return "/"
    if not clean.startswith("/"):
        clean = f"/{clean}"
    return clean.rstrip("/") or "/"


def domain_matches(candidate: str, reference: str, allow_subdomains: bool = True) -> bool:
    candidate_norm = normalize_domain(candidate)
    reference_norm = normalize_domain(reference)
    if candidate_norm == reference_norm:
        return True
    if allow_subdomains and candidate_norm.endswith(f".{reference_norm}"):
        return True
    return False


def domain_equals(candidate: str, reference: str) -> bool:
    return normalize_domain(candidate) == normalize_domain(reference)


def prompt_mentions_token(prompt: str, token: str) -> bool:
    prompt_lower = prompt.lower()
    token_lower = token.lower().strip()
    if not token_lower:
        return False
    if re.search(r"[\u4e00-\u9fff]", token_lower):
        return token_lower in prompt_lower
    pattern = rf"(?<![a-z0-9]){re.escape(token_lower)}(?![a-z0-9])"
    return re.search(pattern, prompt_lower) is not None


def path_matches(candidate_path: str, path_prefixes: list[str]) -> bool:
    if not path_prefixes:
        return True
    candidate_norm = normalize_path(candidate_path)
    for prefix in path_prefixes:
        raw_prefix = str(prefix or "").strip()
        if raw_prefix in {"", "/"}:
            if candidate_norm == "/":
                return True
            continue
        wildcard = raw_prefix.endswith("*")
        prefix_norm = normalize_path(raw_prefix[:-1] if wildcard else raw_prefix)
        if prefix_norm == "/":
            if candidate_norm == "/":
                return True
            continue
        if candidate_norm == prefix_norm or candidate_norm.startswith(f"{prefix_norm}/"):
            return True
        if wildcard and candidate_norm.startswith(prefix_norm):
            return True
    return False


def parse_url_parts(url_or_domain: str) -> tuple[str, str]:
    raw = str(url_or_domain or "").strip()
    if not raw:
        return "", "/"
    parsed = urlparse(raw if "://" in raw else f"http://{raw}")
    domain = normalize_domain(parsed.netloc or parsed.path.split("/", maxsplit=1)[0])
    path = normalize_path(parsed.path if parsed.netloc else "/")
    return domain, path


def _core_domain_label(domain: str) -> str:
    labels = [label for label in normalize_domain(domain).split(".") if label]
    if len(labels) >= 2:
        return labels[-2]
    return labels[0] if labels else ""


def infer_brand_tokens(entity: GroundTruthEntity) -> list[str]:
    tokens: set[str] = set()
    raw_tokens = [entity.name, *entity.aliases]
    raw_tokens.extend(_core_domain_label(domain) for domain in entity.official_domains)
    raw_tokens.extend(_core_domain_label(domain) for domain in entity.authorized_domains)
    for token in raw_tokens:
        cleaned = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(token).lower())
        if len(cleaned) >= 2:
            tokens.add(cleaned)
    return sorted(tokens)


def normalize_entity_key(text: str) -> str:
    cleaned = str(text or "").strip().lower()
    cleaned = re.sub(r"^[`'\"“”‘’<>\[\]{}()（）《》【】]+", "", cleaned)
    cleaned = re.sub(r"[`'\"“”‘’<>\[\]{}()（）《》【】]+$", "", cleaned)
    cleaned = re.sub(r"\s+", "", cleaned)
    changed = True
    while changed and cleaned:
        changed = False
        for suffix in ENTITY_SUFFIXES:
            if cleaned.endswith(suffix) and len(cleaned) > len(suffix):
                cleaned = cleaned[: -len(suffix)]
                changed = True
                break
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", cleaned)


def _normalize_entry_point(index: int, payload: dict, fallback_domain: str, fallback_tier: str) -> TruthEntryPoint:
    domain = normalize_domain(str(payload.get("domain") or fallback_domain))
    entry_id = str(payload.get("entry_id") or f"{domain}:{payload.get('entry_type', 'homepage')}:{index}")
    path_prefixes = payload.get("path_prefixes") or payload.get("paths") or ["/"]
    return TruthEntryPoint(
        entry_id=entry_id,
        domain=domain,
        entry_type=str(payload.get("entry_type") or "homepage"),
        trust_tier=str(payload.get("trust_tier") or fallback_tier or "official"),
        path_prefixes=[normalize_path(path) for path in path_prefixes],
        regions=[str(region) for region in payload.get("regions", [])],
        platform=str(payload.get("platform") or "web"),
        canonical=bool(payload.get("canonical", True)),
        active=bool(payload.get("active", True)),
        tags=[str(tag) for tag in payload.get("tags", [])],
        notes=str(payload.get("notes", "")),
    )


def _synthesized_legacy_entry_points(entity: GroundTruthEntity) -> list[TruthEntryPoint]:
    entry_points: list[TruthEntryPoint] = []
    for index, domain in enumerate(entity.official_domains, start=1):
        entry_points.append(
            TruthEntryPoint(
                entry_id=f"{entity.entity_id}:official:{index}",
                domain=normalize_domain(domain),
                entry_type="homepage",
                trust_tier="official",
                path_prefixes=["/"],
                canonical=index == 1,
            )
        )
    for index, domain in enumerate(entity.authorized_domains, start=1):
        entry_points.append(
            TruthEntryPoint(
                entry_id=f"{entity.entity_id}:authorized:{index}",
                domain=normalize_domain(domain),
                entry_type="resource",
                trust_tier="authorized",
                path_prefixes=["/"],
                canonical=index == 1,
            )
        )
    return entry_points


def _region_applies(prompt_region: str, entry_regions: list[str]) -> bool:
    if not entry_regions:
        return True
    normalized_regions = {str(region).strip().lower() for region in entry_regions if str(region).strip()}
    if prompt_region in {"", "global"}:
        return True
    if "global" in normalized_regions:
        return True
    return str(prompt_region).strip().lower() in normalized_regions


@dataclass(slots=True)
class TruthMatch:
    label: str
    entity_ids: list[str]
    trust_tier: str = "none"
    matched_entry_ids: list[str] = field(default_factory=list)
    matched_entry_types: list[str] = field(default_factory=list)
    entry_match_level: str = "none"


class GroundTruthIndex:
    def __init__(self, entities: list[GroundTruthEntity]):
        normalized_entities: list[GroundTruthEntity] = []
        for entity in entities:
            if not entity.entry_points:
                entity.entry_points = [entry.to_dict() for entry in _synthesized_legacy_entry_points(entity)]
            if not entity.brand_tokens:
                entity.brand_tokens = infer_brand_tokens(entity)
            normalized_entities.append(entity)

        self.entities = normalized_entities
        self.entities_by_id = {entity.entity_id: entity for entity in self.entities}
        self.match_keys_by_entity: dict[str, set[str]] = {
            entity.entity_id: {
                normalized
                for normalized in (
                    normalize_entity_key(entity.entity_id),
                    normalize_entity_key(entity.name),
                    *(normalize_entity_key(alias) for alias in entity.aliases),
                    *(normalize_entity_key(token) for token in entity.brand_tokens),
                )
                if normalized
            }
            for entity in self.entities
        }
        self.entry_points_by_entity: dict[str, list[TruthEntryPoint]] = {
            entity.entity_id: [
                _normalize_entry_point(index, entry, "", entry.get("trust_tier", "official"))
                if isinstance(entry, dict)
                else entry
                for index, entry in enumerate(entity.entry_points, start=1)
            ]
            for entity in self.entities
        }

    @classmethod
    def load(cls, path: Path) -> "GroundTruthIndex":
        if not path.exists():
            return cls([])
        payload = read_json(path)
        entities: list[GroundTruthEntity] = []
        for item in payload.get("entities", []):
            official_domains = [normalize_domain(domain) for domain in item.get("official_domains", [])]
            authorized_domains = [normalize_domain(domain) for domain in item.get("authorized_domains", [])]
            raw_entry_points = item.get("entry_points", [])
            normalized_entry_points = [
                _normalize_entry_point(index, entry, "", entry.get("trust_tier", "official")).to_dict()
                for index, entry in enumerate(raw_entry_points, start=1)
            ]
            entity = GroundTruthEntity(
                entity_id=item["entity_id"],
                name=item["name"],
                entity_type=str(item.get("entity_type", "brand")),
                industry=str(item.get("industry", "")),
                aliases=list(item.get("aliases", [])),
                brand_tokens=[str(token).lower() for token in item.get("brand_tokens", []) if str(token).strip()],
                regions=list(item.get("regions", [])),
                official_domains=official_domains,
                authorized_domains=authorized_domains,
                entry_points=normalized_entry_points,
                notes=str(item.get("notes", "")),
                evidence=list(item.get("evidence", [])),
            )
            if not entity.entry_points:
                entity.entry_points = [entry.to_dict() for entry in _synthesized_legacy_entry_points(entity)]
            if not entity.brand_tokens:
                entity.brand_tokens = infer_brand_tokens(entity)
            entities.append(entity)
        return cls(entities)

    def get_entity(self, entity_id: str) -> GroundTruthEntity | None:
        return self.entities_by_id.get(entity_id)

    def get_entities(self, entity_ids: list[str]) -> list[GroundTruthEntity]:
        return [entity for entity_id in entity_ids if (entity := self.get_entity(entity_id)) is not None]

    def entry_points_for(self, entity: GroundTruthEntity) -> list[TruthEntryPoint]:
        return self.entry_points_by_entity.get(entity.entity_id, [])

    def match_prompt(self, prompt: PromptRecord) -> list[GroundTruthEntity]:
        if prompt.expected_entity:
            expected = normalize_entity_key(prompt.expected_entity)
            matched = [
                entity
                for entity in self.entities
                if expected and expected in self.match_keys_by_entity.get(entity.entity_id, set())
            ]
            if matched:
                return matched

        lowered_prompt = prompt.prompt.lower()
        matched: list[GroundTruthEntity] = []
        for entity in self.entities:
            candidates = [entity.name, *entity.aliases, *entity.brand_tokens]
            if any(prompt_mentions_token(lowered_prompt, token) for token in candidates):
                matched.append(entity)
        return matched

    def _build_match(self, pairs: list[tuple[GroundTruthEntity, TruthEntryPoint]], level: str) -> TruthMatch:
        if not pairs:
            return TruthMatch(label="no_truth_match", entity_ids=[], trust_tier="none", entry_match_level="none")
        entity, entry = pairs[0]
        trust_tier = entry.trust_tier
        return TruthMatch(
            label=trust_tier,
            entity_ids=[entity.entity_id],
            trust_tier=trust_tier,
            matched_entry_ids=[entry.entry_id],
            matched_entry_types=[entry.entry_type],
            entry_match_level=level,
        )

    def classify_url(self, prompt: PromptRecord, url_or_domain: str, allow_subdomains: bool = True) -> TruthMatch:
        matched_entities = self.match_prompt(prompt)
        if not matched_entities:
            return TruthMatch(label="no_truth_match", entity_ids=[], trust_tier="none", entry_match_level="no_truth")

        candidate_domain, candidate_path = parse_url_parts(url_or_domain)
        expected_entry_types = set(prompt.expected_entry_types)
        same_domain_entries: list[tuple[GroundTruthEntity, TruthEntryPoint]] = []
        exact_entries: list[tuple[GroundTruthEntity, TruthEntryPoint]] = []

        for entity in matched_entities:
            for entry in self.entry_points_for(entity):
                if not entry.active:
                    continue
                if not _region_applies(prompt.region, entry.regions):
                    continue
                if not domain_matches(candidate_domain, entry.domain, allow_subdomains):
                    continue
                same_domain_entries.append((entity, entry))
                if path_matches(candidate_path, entry.path_prefixes):
                    exact_entries.append((entity, entry))

        def sort_pairs(pairs: list[tuple[GroundTruthEntity, TruthEntryPoint]]) -> list[tuple[GroundTruthEntity, TruthEntryPoint]]:
            return sorted(
                pairs,
                key=lambda pair: (
                    0 if domain_equals(candidate_domain, pair[1].domain) else 1,
                    0 if pair[1].trust_tier == "official" else 1,
                    0 if pair[1].canonical else 1,
                    pair[1].entry_type,
                ),
            )

        if expected_entry_types:
            exact_expected = sort_pairs(
                [pair for pair in exact_entries if pair[1].entry_type in expected_entry_types]
            )
            if exact_expected:
                return self._build_match(exact_expected, "exact_entry")

            same_domain_expected = sort_pairs(
                [pair for pair in same_domain_entries if pair[1].entry_type in expected_entry_types]
            )
            if same_domain_expected:
                return self._build_match(same_domain_expected, "expected_type_same_domain")

            exact_any = sort_pairs(exact_entries)
            if exact_any:
                return self._build_match(exact_any, "wrong_entry_type")
        else:
            exact_any = sort_pairs(exact_entries)
            if exact_any:
                return self._build_match(exact_any, "catalogued_entry")

        if same_domain_entries:
            return self._build_match(sort_pairs(same_domain_entries), "domain_only")

        exact_authorized_hits = [
            entity.entity_id
            for entity in matched_entities
            if any(domain_equals(candidate_domain, ref) for ref in entity.authorized_domains)
        ]
        if exact_authorized_hits:
            return TruthMatch(
                label="authorized",
                entity_ids=exact_authorized_hits,
                trust_tier="authorized",
                entry_match_level="domain_only",
            )

        exact_official_hits = [
            entity.entity_id
            for entity in matched_entities
            if any(domain_equals(candidate_domain, ref) for ref in entity.official_domains)
        ]
        if exact_official_hits:
            return TruthMatch(
                label="official",
                entity_ids=exact_official_hits,
                trust_tier="official",
                entry_match_level="domain_only",
            )

        authorized_hits = [
            entity.entity_id
            for entity in matched_entities
            if any(domain_matches(candidate_domain, ref, allow_subdomains) for ref in entity.authorized_domains)
        ]
        if authorized_hits:
            return TruthMatch(
                label="authorized",
                entity_ids=authorized_hits,
                trust_tier="authorized",
                entry_match_level="domain_only",
            )

        official_hits = [
            entity.entity_id
            for entity in matched_entities
            if any(domain_matches(candidate_domain, ref, allow_subdomains) for ref in entity.official_domains)
        ]
        if official_hits:
            return TruthMatch(
                label="official",
                entity_ids=official_hits,
                trust_tier="official",
                entry_match_level="domain_only",
            )

        return TruthMatch(
            label="unofficial",
            entity_ids=[entity.entity_id for entity in matched_entities],
            trust_tier="unofficial",
            entry_match_level="off_brand",
        )

    def classify_domain(self, prompt: PromptRecord, domain: str, allow_subdomains: bool = True) -> TruthMatch:
        return self.classify_url(prompt, domain, allow_subdomains)


def write_truth_template(path: Path) -> None:
    template = {
        "entities": [
            {
                "entity_id": "example_entity",
                "name": "Example Brand",
                "entity_type": "brand",
                "industry": "general",
                "aliases": ["Example", "Example Official"],
                "brand_tokens": ["example"],
                "regions": ["global"],
                "official_domains": ["example.com"],
                "authorized_domains": ["docs.example.com", "login.example.com"],
                "entry_points": [
                    {
                        "entry_id": "example.homepage",
                        "domain": "example.com",
                        "entry_type": "homepage",
                        "trust_tier": "official",
                        "path_prefixes": ["/"],
                        "canonical": True,
                        "regions": ["global"],
                    },
                    {
                        "entry_id": "example.login",
                        "domain": "login.example.com",
                        "entry_type": "login",
                        "trust_tier": "authorized",
                        "path_prefixes": ["/", "/signin"],
                        "canonical": True,
                        "regions": ["global"],
                    },
                ],
                "notes": "Replace this template with curated official and authorized entry points.",
                "evidence": [
                    {
                        "source": "official_documentation",
                        "url": "https://example.com",
                        "checked_at": "2026-03-30",
                    }
                ],
            }
        ]
    }
    write_json(path, template)


def summarize_truth_index(index: GroundTruthIndex) -> dict[str, dict[str, int] | int]:
    by_industry: dict[str, int] = {}
    by_entity_type: dict[str, int] = {}
    by_region: dict[str, int] = {}
    by_entry_type: dict[str, int] = {}
    by_trust_tier: dict[str, int] = {}

    for entity in index.entities:
        by_industry[entity.industry or "unknown"] = by_industry.get(entity.industry or "unknown", 0) + 1
        by_entity_type[entity.entity_type or "unknown"] = by_entity_type.get(entity.entity_type or "unknown", 0) + 1
        for region in entity.regions or ["global"]:
            by_region[region] = by_region.get(region, 0) + 1
        for entry in index.entry_points_for(entity):
            by_entry_type[entry.entry_type] = by_entry_type.get(entry.entry_type, 0) + 1
            by_trust_tier[entry.trust_tier] = by_trust_tier.get(entry.trust_tier, 0) + 1

    return {
        "entity_count": len(index.entities),
        "by_industry": dict(sorted(by_industry.items())),
        "by_entity_type": dict(sorted(by_entity_type.items())),
        "by_region": dict(sorted(by_region.items())),
        "by_entry_type": dict(sorted(by_entry_type.items())),
        "by_trust_tier": dict(sorted(by_trust_tier.items())),
    }
