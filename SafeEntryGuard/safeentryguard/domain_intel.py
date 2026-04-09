from __future__ import annotations

import json
import shutil
import subprocess
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any

try:
    import tldextract
except Exception:  # pragma: no cover
    tldextract = None

from .truth_store import normalize_domain


SUSPICIOUS_KEYWORDS = ("secure", "verify", "update", "wallet", "bonus", "gift", "support", "login")


def registrable_domain(domain: str) -> str:
    normalized = normalize_domain(domain)
    if tldextract is None:
        labels = [label for label in normalized.split(".") if label]
        if len(labels) >= 2:
            return ".".join(labels[-2:])
        return normalized
    extracted = tldextract.extract(normalized)
    if not extracted.domain or not extracted.suffix:
        return normalized
    return f"{extracted.domain}.{extracted.suffix}"


def _digit_swap_flag(label: str) -> bool:
    return any(char.isdigit() for char in label)


def _similarity(candidate: str, references: list[str]) -> tuple[float, str]:
    best_score = 0.0
    best_reference = ""
    for reference in references:
        score = SequenceMatcher(None, candidate, reference).ratio()
        if score > best_score:
            best_score = score
            best_reference = reference
    return best_score, best_reference


@lru_cache(maxsize=64)
def _dnstwist_variants(official_domain: str, dnstwist_path: str) -> set[str]:
    binary = shutil.which(dnstwist_path) or shutil.which("dnstwist")
    if not binary:
        return set()
    try:
        completed = subprocess.run(
            [binary, "--format", "json", official_domain],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception:
        return set()
    if completed.returncode != 0 or not completed.stdout.strip():
        return set()
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return set()
    return {
        normalize_domain(row.get("domain", ""))
        for row in payload
        if normalize_domain(row.get("domain", ""))
    }


def analyze_domain(
    domain: str,
    *,
    official_domains: list[str] | None = None,
    use_dnstwist: bool = False,
    dnstwist_path: str = "dnstwist",
) -> dict[str, Any]:
    normalized = normalize_domain(domain)
    registrable = registrable_domain(normalized)
    labels = [label for label in normalized.split(".") if label]
    official_registrables = [registrable_domain(reference) for reference in (official_domains or []) if reference]
    similarity_score, similar_reference = _similarity(registrable, official_registrables)
    suspicious_flags = {
        "unicode_domain": any(ord(char) > 127 for char in normalized),
        "punycode_domain": normalized.startswith("xn--") or ".xn--" in normalized,
        "digit_swap": _digit_swap_flag(registrable.split(".", maxsplit=1)[0]),
        "long_subdomain_chain": len(labels) >= 4,
        "many_hyphens": normalized.count("-") >= 2,
        "suspicious_keyword": any(keyword in normalized for keyword in SUSPICIOUS_KEYWORDS),
        "looks_like_typosquat": similarity_score >= 0.78 and similarity_score < 1.0,
    }
    dnstwist_match = False
    if use_dnstwist and official_domains:
        for reference in official_domains:
            if normalized in _dnstwist_variants(reference, dnstwist_path):
                dnstwist_match = True
                suspicious_flags["dnstwist_match"] = True
                break
    lexical_score = sum(1.0 for value in suspicious_flags.values() if value) / max(1, len(suspicious_flags))
    return {
        "domain": normalized,
        "registrable_domain": registrable,
        "lexical_flags": suspicious_flags,
        "similarity_to_official": round(similarity_score, 4),
        "similar_official_domain": similar_reference,
        "dnstwist_match": dnstwist_match,
        "lexical_score": round(lexical_score, 4),
    }
