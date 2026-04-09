from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlparse

from .schemas import Entity, EntityInference, EntryPoint, MatchResult
from .utils import read_json


ENTRY_TYPE_KEYWORDS = {
    "login": ("login", "sign in", "signin", "account", "auth", "登录", "登陆", "账号", "账户"),
    "payment": ("payment", "pay", "billing", "wallet", "checkout", "支付", "付款", "缴费", "钱包"),
    "download": ("download", "install", "setup", "client", "下载安装", "下载", "安装", "客户端"),
    "support": ("support", "help", "help center", "customer service", "客服", "帮助", "帮助中心", "工单"),
    "docs": ("docs", "documentation", "developer", "api", "文档", "开发者", "api"),
    "homepage": ("official website", "homepage", "official site", "官网", "官方网站", "官网地址"),
}


def normalize_domain(domain: str) -> str:
    return str(domain or "").strip().lower().rstrip(".")


def normalize_path(path: str) -> str:
    candidate = str(path or "/").strip()
    if not candidate.startswith("/"):
        candidate = f"/{candidate}"
    return candidate.rstrip("/") or "/"


def parse_url_parts(url_or_domain: str) -> tuple[str, str]:
    raw = str(url_or_domain or "").strip()
    if not raw:
        return "", "/"
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    domain = normalize_domain(parsed.netloc or parsed.path.split("/", maxsplit=1)[0])
    path = normalize_path(parsed.path if parsed.netloc else "/")
    return domain, path


def _normalize_token(token: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(token or "").lower())


def _mentions_token(text: str, token: str) -> bool:
    text_lower = str(text or "").lower()
    token_lower = str(token or "").lower().strip()
    if not token_lower:
        return False
    if re.search(r"[\u4e00-\u9fff]", token_lower):
        return token_lower in text_lower
    pattern = rf"(?<![a-z0-9]){re.escape(token_lower)}(?![a-z0-9])"
    return re.search(pattern, text_lower) is not None


def _path_matches(candidate_path: str, prefixes: list[str]) -> bool:
    if not prefixes:
        return True
    normalized = normalize_path(candidate_path)
    for prefix in prefixes:
        raw = str(prefix or "").strip()
        wildcard = raw.endswith("*")
        prefix_norm = normalize_path(raw[:-1] if wildcard else raw or "/")
        if prefix_norm == "/":
            if normalized == "/":
                return True
            continue
        if normalized == prefix_norm or normalized.startswith(f"{prefix_norm}/"):
            return True
        if wildcard and normalized.startswith(prefix_norm):
            return True
    return False


class TruthStore:
    def __init__(self, entities: list[Entity]):
        self.entities = entities
        self.by_id = {entity.entity_id: entity for entity in entities}

    @classmethod
    def load(cls, path: str | Path) -> "TruthStore":
        payload = read_json(path)
        entity_rows = payload["entities"] if isinstance(payload, dict) else payload
        entities: list[Entity] = []
        for row in entity_rows:
            entry_points = [
                EntryPoint(
                    entry_id=str(entry.get("entry_id") or ""),
                    domain=normalize_domain(entry.get("domain") or ""),
                    entry_type=str(entry.get("entry_type") or "homepage"),
                    trust_tier=str(entry.get("trust_tier") or "official"),
                    path_prefixes=[normalize_path(path_prefix) for path_prefix in (entry.get("path_prefixes") or ["/"])],
                )
                for entry in row.get("entry_points", [])
            ]
            entities.append(
                Entity(
                    entity_id=str(row.get("entity_id") or ""),
                    name=str(row.get("name") or ""),
                    aliases=[str(alias) for alias in row.get("aliases", [])],
                    brand_tokens=[str(token) for token in row.get("brand_tokens", [])],
                    official_domains=[normalize_domain(domain) for domain in row.get("official_domains", [])],
                    authorized_domains=[normalize_domain(domain) for domain in row.get("authorized_domains", [])],
                    entry_points=entry_points,
                )
            )
        return cls(entities)

    def summarize(self) -> dict:
        return {
            "entity_count": len(self.entities),
            "entities": [entity.entity_id for entity in self.entities],
        }

    def find_entity(self, entity_id: str) -> Entity | None:
        return self.by_id.get(entity_id)

    def infer_entity(self, prompt: str, explicit_entity: str = "") -> EntityInference | None:
        if explicit_entity:
            normalized_target = _normalize_token(explicit_entity)
            for entity in self.entities:
                candidates = {
                    _normalize_token(entity.entity_id),
                    _normalize_token(entity.name),
                    *(_normalize_token(alias) for alias in entity.aliases),
                    *(_normalize_token(token) for token in entity.brand_tokens),
                }
                if normalized_target in candidates:
                    return EntityInference(entity_id=entity.entity_id, confidence=1.0, matched_terms=[explicit_entity])

        best: EntityInference | None = None
        for entity in self.entities:
            matched_terms: list[str] = []
            score = 0.0
            search_terms = [
                entity.name,
                *entity.aliases,
                *entity.brand_tokens,
                *(domain.split(".")[0] for domain in entity.official_domains),
            ]
            for term in search_terms:
                if _mentions_token(prompt, term):
                    normalized = _normalize_token(term)
                    if normalized and normalized not in matched_terms:
                        matched_terms.append(normalized)
                        score += 0.55 if len(normalized) <= 4 else 0.75
            if score <= 0:
                continue
            confidence = min(1.0, score / 1.5)
            if best is None or confidence > best.confidence:
                best = EntityInference(entity_id=entity.entity_id, confidence=confidence, matched_terms=matched_terms)
        return best

    def infer_requested_entry_types(self, prompt: str, explicit_entry_types: list[str] | None = None) -> list[str]:
        if explicit_entry_types:
            return sorted({str(entry_type).lower() for entry_type in explicit_entry_types if str(entry_type).strip()})
        prompt_lower = str(prompt or "").lower()
        matched: list[str] = []
        for entry_type, keywords in ENTRY_TYPE_KEYWORDS.items():
            if any(keyword.lower() in prompt_lower for keyword in keywords):
                matched.append(entry_type)
        return sorted(set(matched)) or ["homepage"]

    def match_candidate(self, url_or_domain: str, entity: Entity | None, requested_entry_types: list[str]) -> MatchResult:
        if entity is None:
            return MatchResult()
        domain, path = parse_url_parts(url_or_domain)
        if not domain:
            return MatchResult(entity_id=entity.entity_id)

        if domain in entity.official_domains:
            domain_label = "official"
            trust_tier = "official"
        elif domain in entity.authorized_domains:
            domain_label = "authorized"
            trust_tier = "authorized"
        elif any(domain.endswith(f".{official}") for official in entity.official_domains):
            domain_label = "official_subdomain"
            trust_tier = "official"
        elif any(domain.endswith(f".{authorized}") for authorized in entity.authorized_domains):
            domain_label = "authorized_subdomain"
            trust_tier = "authorized"
        else:
            return MatchResult(entity_id=entity.entity_id, domain_label="unmatched")

        exact_types: list[str] = []
        same_domain_types: list[str] = []
        for entry in entity.entry_points:
            if normalize_domain(entry.domain) != domain:
                continue
            same_domain_types.append(entry.entry_type)
            if entry.entry_type in requested_entry_types and _path_matches(path, entry.path_prefixes):
                exact_types.append(entry.entry_type)

        if exact_types:
            return MatchResult(
                entity_id=entity.entity_id,
                domain_label=domain_label,
                entry_match_level="exact",
                trust_tier=trust_tier,
                matched_entry_types=sorted(set(exact_types)),
            )
        if same_domain_types:
            return MatchResult(
                entity_id=entity.entity_id,
                domain_label=domain_label,
                entry_match_level="same_domain",
                trust_tier=trust_tier,
                matched_entry_types=sorted(set(same_domain_types)),
            )
        return MatchResult(
            entity_id=entity.entity_id,
            domain_label=domain_label,
            entry_match_level="domain_only",
            trust_tier=trust_tier,
        )


def entity_to_dict(entity: Entity) -> dict:
    payload = asdict(entity)
    payload["entry_points"] = [asdict(entry) for entry in entity.entry_points]
    return payload
