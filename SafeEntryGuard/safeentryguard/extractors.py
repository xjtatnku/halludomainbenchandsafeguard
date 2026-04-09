from __future__ import annotations

import re
from urllib.parse import urlparse

from .schemas import Candidate
from .truth_store import normalize_domain, normalize_path


URL_PATTERN = re.compile(r"(?i)\bhttps?://[^\s<>\]\[\"'`]+")
DOMAIN_PATTERN = re.compile(
    r"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?:/[^\s<>\]\[\"'`]*)?"
)
TRAILING_NOISE = ".,;:!?)]}>\u3002\uff0c\uff1b\uff1a\uff01\uff1f\u3001"
PURE_SUFFIXES = {"com", "org", "net", "edu", "gov", "co.uk", "cn", "com.cn"}


def _clean_candidate(raw: str) -> str:
    candidate = str(raw or "").strip().strip("`").strip()
    candidate = candidate.rstrip(TRAILING_NOISE)
    candidate = re.sub(r"[)\]]+$", "", candidate)
    return candidate.strip()


def _normalize_candidate(raw: str) -> tuple[str, str, str]:
    candidate = _clean_candidate(raw)
    if not candidate:
        return "", "", ""
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    domain = normalize_domain(parsed.netloc or parsed.path.split("/", maxsplit=1)[0])
    path = normalize_path(parsed.path if parsed.netloc else "/")
    if domain in PURE_SUFFIXES or domain.count(".") == 0:
        return "", "", ""
    normalized_url = f"{parsed.scheme or 'https'}://{domain}{path}"
    return normalized_url, domain, path


def extract_candidates(response_text: str) -> list[Candidate]:
    text = str(response_text or "")
    matches: list[str] = []
    matches.extend(URL_PATTERN.findall(text))
    matches.extend(DOMAIN_PATTERN.findall(text))
    seen: set[str] = set()
    candidates: list[Candidate] = []
    for raw in matches:
        normalized_url, domain, path = _normalize_candidate(raw)
        if not normalized_url or normalized_url in seen:
            continue
        seen.add(normalized_url)
        scheme = urlparse(normalized_url).scheme or "https"
        candidates.append(
            Candidate(
                raw_text=raw,
                normalized_url=normalized_url,
                domain=domain,
                path=path,
                scheme=scheme,
                position=len(candidates) + 1,
            )
        )
    return candidates
