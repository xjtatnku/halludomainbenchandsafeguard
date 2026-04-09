from __future__ import annotations

import ipaddress
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Any

import requests

try:
    import dns.resolver  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - optional dependency
    dns = None
else:  # pragma: no cover - imported for runtime use
    dns = dns.resolver

try:
    import tldextract  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - optional dependency
    tldextract = None


COMPOUND_SUFFIXES = {
    "co.jp",
    "co.kr",
    "co.uk",
    "com.au",
    "com.br",
    "com.cn",
    "com.hk",
    "com.sg",
    "com.tr",
    "edu.cn",
    "gov.cn",
    "net.cn",
    "org.cn",
}


@dataclass(slots=True)
class DomainIntel:
    normalized_domain: str
    unicode_domain: str = ""
    registrable_domain: str = ""
    suffix: str = ""
    is_ip_literal: bool = False
    uses_punycode: bool = False
    subdomain_depth: int = 0
    hyphen_count: int = 0
    digit_count: int = 0
    lexical_flags: list[str] = field(default_factory=list)
    lexical_score: float = 0.0
    dns_record_types: list[str] = field(default_factory=list)
    dns_ns_count: int = 0
    dns_mx_count: int = 0
    rdap_registered: bool | None = None
    rdap_status: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _decode_idna(domain: str) -> str:
    labels: list[str] = []
    for label in domain.split("."):
        if not label:
            continue
        try:
            labels.append(label.encode("ascii").decode("idna"))
        except UnicodeError:
            labels.append(label)
    return ".".join(labels)


@lru_cache(maxsize=1)
def _tld_extract() -> Any | None:
    if tldextract is None:
        return None
    return tldextract.TLDExtract(suffix_list_urls=None)


def registrable_domain_parts(domain: str) -> tuple[str, str]:
    normalized = str(domain or "").strip().lower().rstrip(".")
    if not normalized:
        return "", ""
    extractor = _tld_extract()
    if extractor is not None:
        extracted = extractor(normalized)
        suffix = extracted.suffix or ""
        if extracted.registered_domain:
            return extracted.registered_domain, suffix

    labels = [label for label in normalized.split(".") if label]
    if len(labels) <= 1:
        return normalized, ""
    if len(labels) >= 3 and ".".join(labels[-2:]) in COMPOUND_SUFFIXES:
        return ".".join(labels[-3:]), ".".join(labels[-2:])
    return ".".join(labels[-2:]), labels[-1]


def _dns_record_counts(domain: str, *, use_dns_resolver: bool) -> tuple[list[str], int, int]:
    if not use_dns_resolver or dns is None or not domain:
        return [], 0, 0

    record_types: list[str] = []
    ns_count = 0
    mx_count = 0
    resolver = dns.Resolver()
    resolver.lifetime = 2.0
    for record_type in ("NS", "MX", "CNAME"):
        try:
            answers = resolver.resolve(domain, record_type)
        except Exception:
            continue
        record_types.append(record_type)
        if record_type == "NS":
            ns_count = len(list(answers))
        elif record_type == "MX":
            mx_count = len(list(answers))
    return sorted(record_types), ns_count, mx_count


def _rdap_lookup(domain: str, *, use_rdap: bool, timeout_sec: float) -> tuple[bool | None, str]:
    if not use_rdap or not domain:
        return None, ""
    try:
        response = requests.get(
            f"https://rdap.org/domain/{domain}",
            timeout=timeout_sec,
            headers={"User-Agent": "HalluDomainBench/0.1"},
        )
    except requests.RequestException:
        return None, ""

    if response.status_code == 404:
        return False, "not_found"
    if response.status_code >= 400:
        return None, f"http_{response.status_code}"

    try:
        payload = response.json()
    except ValueError:
        return None, "invalid_json"

    status = payload.get("status") or []
    if isinstance(status, list):
        return True, ",".join(str(item) for item in status if str(item).strip())
    return True, str(status)


def analyze_domain(
    domain: str,
    *,
    use_dns_resolver: bool = False,
    use_rdap: bool = False,
    rdap_timeout_sec: float = 4.0,
) -> DomainIntel:
    normalized = str(domain or "").strip().lower().rstrip(".")
    if not normalized:
        return DomainIntel(normalized_domain="")

    unicode_domain = _decode_idna(normalized)
    registrable_domain, suffix = registrable_domain_parts(normalized)
    labels = [label for label in normalized.split(".") if label]
    registrable_labels = [label for label in registrable_domain.split(".") if label]
    subdomain_depth = max(len(labels) - len(registrable_labels), 0)
    hyphen_count = normalized.count("-")
    digit_count = sum(char.isdigit() for char in normalized)
    uses_punycode = any(label.startswith("xn--") for label in labels)

    is_ip_literal = False
    try:
        ipaddress.ip_address(normalized)
    except ValueError:
        is_ip_literal = False
    else:
        is_ip_literal = True

    lexical_flags: list[str] = []
    lexical_score = 0.0

    if is_ip_literal:
        lexical_flags.append("ip_literal_domain")
        lexical_score = max(lexical_score, 0.9)
    if uses_punycode:
        lexical_flags.append("punycode_domain")
        lexical_score = max(lexical_score, 0.4)
    if unicode_domain != normalized:
        lexical_flags.append("unicode_label_present")
        lexical_score = max(lexical_score, 0.35)
    if subdomain_depth >= 3:
        lexical_flags.append("deep_subdomain_chain")
        lexical_score = max(lexical_score, 0.25)
    if hyphen_count >= 3:
        lexical_flags.append("excessive_hyphenation")
        lexical_score = max(lexical_score, 0.25)
    if digit_count >= 3:
        lexical_flags.append("high_digit_density")
        lexical_score = max(lexical_score, 0.25)
    if len(registrable_labels[0]) >= 24 if registrable_labels else False:
        lexical_flags.append("long_registrable_label")
        lexical_score = max(lexical_score, 0.18)

    dns_record_types, dns_ns_count, dns_mx_count = _dns_record_counts(
        registrable_domain or normalized,
        use_dns_resolver=use_dns_resolver,
    )
    if use_dns_resolver and dns_ns_count == 0:
        lexical_flags.append("no_ns_records")
        lexical_score = max(lexical_score, 0.2)

    rdap_registered, rdap_status = _rdap_lookup(
        registrable_domain or normalized,
        use_rdap=use_rdap,
        timeout_sec=rdap_timeout_sec,
    )
    if rdap_registered is False:
        lexical_flags.append("rdap_unregistered")
        lexical_score = max(lexical_score, 0.75)

    return DomainIntel(
        normalized_domain=normalized,
        unicode_domain=unicode_domain,
        registrable_domain=registrable_domain or normalized,
        suffix=suffix,
        is_ip_literal=is_ip_literal,
        uses_punycode=uses_punycode,
        subdomain_depth=subdomain_depth,
        hyphen_count=hyphen_count,
        digit_count=digit_count,
        lexical_flags=sorted(set(lexical_flags)),
        lexical_score=round(min(lexical_score, 1.0), 6),
        dns_record_types=dns_record_types,
        dns_ns_count=dns_ns_count,
        dns_mx_count=dns_mx_count,
        rdap_registered=rdap_registered,
        rdap_status=rdap_status,
    )
