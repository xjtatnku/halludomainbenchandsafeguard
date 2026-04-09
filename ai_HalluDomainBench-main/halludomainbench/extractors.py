from __future__ import annotations

import re
from typing import Iterable, Mapping, Sequence
from urllib.parse import urlparse

from .schemas import ExtractedLink


MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^)\s]+)\)", re.I)
URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"\]\[(){}，。；、]+", re.I)
BARE_DOMAIN_RE = re.compile(
    r"(?<!@)\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]*)?",
    re.I,
)
DOMAIN_ONLY_RE = re.compile(r"^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$")
URL_SAFE_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~:/?#[]@!$&'()+,;=%")
FILELIKE_TLDS = {
    "apk",
    "bin",
    "css",
    "csv",
    "dmg",
    "doc",
    "docx",
    "exe",
    "gif",
    "htm",
    "html",
    "ico",
    "jpeg",
    "jpg",
    "js",
    "json",
    "md",
    "msi",
    "pdf",
    "php",
    "png",
    "rar",
    "svg",
    "tar",
    "tgz",
    "txt",
    "woff",
    "woff2",
    "xls",
    "xlsx",
    "xml",
    "yaml",
    "yml",
    "zip",
}


def _truncate_to_url_chars(raw: str) -> str:
    buffer: list[str] = []
    for char in raw:
        if char in URL_SAFE_CHARS:
            buffer.append(char)
            continue
        break
    return "".join(buffer)


def _strip_candidate(raw: str) -> str:
    cleaned = raw.strip().strip("`'\"<>[](){}")
    cleaned = cleaned.rstrip(".,;:，。；、)]}*>")
    cleaned = re.split(r"[\u3002\uff1b\uff0c]\s*", cleaned, maxsplit=1)[0]
    cleaned = re.split(r"\s+", cleaned, maxsplit=1)[0]
    return _truncate_to_url_chars(cleaned)


def _looks_like_file_reference(raw: str, host: str) -> bool:
    labels = [label for label in host.split(".") if label]
    if len(labels) != 2:
        return False
    tld = labels[-1].lower()
    if tld not in FILELIKE_TLDS:
        return False
    lowered_raw = raw.lower()
    return not lowered_raw.startswith(("http://", "https://", "www."))


def _canonicalize(raw: str) -> tuple[str, str] | None:
    candidate = _strip_candidate(raw)
    if "](" in candidate:
        candidate = candidate.split("](", maxsplit=1)[-1]
    if not candidate:
        return None
    if candidate.startswith("www.") or DOMAIN_ONLY_RE.match(candidate.split("/", maxsplit=1)[0]):
        candidate = f"http://{candidate}"

    parsed = urlparse(candidate)
    scheme = parsed.scheme or "http"
    netloc = (parsed.netloc or parsed.path.split("/", maxsplit=1)[0]).lower().rstrip(".")
    if not netloc or "." not in netloc:
        return None
    if _looks_like_file_reference(raw, netloc):
        return None
    path = parsed.path if parsed.netloc else ""
    query = f"?{parsed.query}" if parsed.query else ""
    normalized = f"{scheme}://{netloc}{path}{query}".rstrip("/")
    return normalized, netloc


def extract_links_from_text(text: str, source_field: str) -> list[ExtractedLink]:
    candidates: list[str] = []
    candidates.extend(MARKDOWN_LINK_RE.findall(text))
    candidates.extend(URL_RE.findall(text))
    candidates.extend(BARE_DOMAIN_RE.findall(text))

    extracted: list[ExtractedLink] = []
    seen: dict[str, ExtractedLink] = {}
    for raw in candidates:
        canonical = _canonicalize(raw)
        if not canonical:
            continue
        url, domain = canonical
        key = f"{domain}|{url.split(domain, maxsplit=1)[-1]}"
        position = len(extracted) + 1
        link = ExtractedLink(raw=raw, url=url, domain=domain, source_field=source_field, position=position)
        existing = seen.get(key)
        if existing:
            if existing.url.startswith("http://") and link.url.startswith("https://"):
                seen[key] = link
            continue
        seen[key] = link
        extracted.append(link)
    return extracted


def extract_links_from_fields(payload: Mapping[str, str], source_fields: Sequence[str]) -> list[ExtractedLink]:
    extracted: list[ExtractedLink] = []
    for field in source_fields:
        text = str(payload.get(field, "") or "")
        if not text.strip():
            continue
        extracted.extend(extract_links_from_text(text, field))
    return extracted


def domains_only(links: Iterable[ExtractedLink]) -> list[str]:
    return [link.domain for link in links]
