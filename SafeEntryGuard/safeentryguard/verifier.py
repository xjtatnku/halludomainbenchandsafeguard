from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import requests

try:
    import dns.resolver
except Exception:  # pragma: no cover
    dns = None

from .config import VerificationConfig
from .domain_intel import analyze_domain
from .truth_store import normalize_domain


def _resolve_dns(domain: str) -> dict[str, Any]:
    if dns is None:
        return {"enabled": False, "resolved": None, "records": {}}
    records: dict[str, list[str]] = {}
    resolved = False
    for record_type in ("A", "AAAA", "CNAME"):
        try:
            answers = dns.resolver.resolve(domain, record_type, lifetime=3.0)
            values = [str(answer).strip() for answer in answers]
            if values:
                resolved = True
                records[record_type] = values
        except Exception:
            continue
    return {"enabled": True, "resolved": resolved, "records": records}


def _query_rdap(domain: str, config: VerificationConfig) -> dict[str, Any]:
    url = config.rdap_url_template.format(domain=domain)
    try:
        response = requests.get(url, timeout=config.request_timeout_sec)
        if response.status_code == 200:
            payload = response.json()
            return {
                "queried": True,
                "registered": True,
                "status_code": response.status_code,
                "handle": payload.get("handle", ""),
            }
        if response.status_code == 404:
            return {"queried": True, "registered": False, "status_code": 404}
        return {"queried": True, "registered": None, "status_code": response.status_code}
    except Exception as exc:
        return {"queried": False, "registered": None, "error": str(exc)}


def verify_candidate(
    url: str,
    *,
    verification: VerificationConfig,
    official_domains: list[str] | None = None,
) -> dict[str, Any]:
    domain = normalize_domain(urlparse(url).netloc)
    intel = analyze_domain(
        domain,
        official_domains=official_domains or [],
        use_dnstwist=verification.use_dnstwist,
        dnstwist_path=verification.dnstwist_path,
    )
    proxies = None
    if verification.proxy_url:
        proxies = {"http": verification.proxy_url, "https": verification.proxy_url}

    http_status = None
    final_url = ""
    final_domain = ""
    live = None
    error = ""
    if verification.allow_http_verification:
        try:
            response = requests.get(
                url,
                timeout=verification.request_timeout_sec,
                allow_redirects=True,
                headers={"User-Agent": verification.user_agent},
                proxies=proxies,
            )
            http_status = response.status_code
            final_url = response.url
            final_domain = normalize_domain(urlparse(final_url).netloc)
            live = response.ok
        except Exception as exc:
            error = str(exc)

    dns_result = {"enabled": False, "resolved": None, "records": {}}
    if verification.use_dns_resolver:
        dns_result = _resolve_dns(domain)

    rdap_result = {"queried": False, "registered": None}
    if verification.use_rdap:
        rdap_result = _query_rdap(intel["registrable_domain"], verification)

    live_status = "live" if live else ("dead" if live is False else "unknown")
    if verification.use_dns_resolver and dns_result.get("resolved") is False and not final_url:
        live_status = "dead"

    redirect_drift = bool(final_domain) and final_domain not in {"", domain}
    return {
        "url": url,
        "domain": domain,
        "http_status": http_status,
        "final_url": final_url,
        "final_domain": final_domain,
        "live_status": live_status,
        "error": error,
        "redirect_drift": redirect_drift,
        "dns": dns_result,
        "rdap": rdap_result,
        "domain_intel": intel,
    }
