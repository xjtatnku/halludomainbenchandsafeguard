from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .utils import PROJECT_ROOT, read_json, resolve_path


@dataclass(slots=True)
class VerificationConfig:
    request_timeout_sec: float = 8.0
    allow_http_verification: bool = True
    proxy_url: str = ""
    user_agent: str = "SafeEntryGuard/0.1"
    use_dns_resolver: bool = False
    use_rdap: bool = False
    rdap_url_template: str = "https://rdap.org/domain/{domain}"
    use_dnstwist: bool = False
    dnstwist_path: str = "dnstwist"


@dataclass(slots=True)
class PolicyConfig:
    minimum_recommendation_score: float = 0.55
    allow_same_domain_fallback: bool = True
    require_exact_entry_for_sensitive_intents: bool = True
    suspicion_weight: float = 0.45


@dataclass(slots=True)
class OutputConfig:
    default_jsonl_output: Path
    default_summary_output: Path


@dataclass(slots=True)
class ApiConfig:
    host: str = "127.0.0.1"
    port: int = 8765


@dataclass(slots=True)
class GuardConfig:
    root_dir: Path
    project_name: str
    truth_store_path: Path
    verification: VerificationConfig
    policy: PolicyConfig
    output: OutputConfig
    api: ApiConfig


DEFAULT_CONFIG: dict[str, Any] = {
    "project_name": "SafeEntryGuard",
    "truth_store_path": "data/truth/entities.sample.json",
    "verification": {
        "request_timeout_sec": 8.0,
        "allow_http_verification": True,
        "proxy_url": "",
        "user_agent": "SafeEntryGuard/0.1",
        "use_dns_resolver": False,
        "use_rdap": False,
        "rdap_url_template": "https://rdap.org/domain/{domain}",
        "use_dnstwist": False,
        "dnstwist_path": "dnstwist",
    },
    "policy": {
        "minimum_recommendation_score": 0.55,
        "allow_same_domain_fallback": True,
        "require_exact_entry_for_sensitive_intents": True,
        "suspicion_weight": 0.45,
    },
    "output": {
        "default_jsonl_output": "outputs/filtered_results.jsonl",
        "default_summary_output": "outputs/filtered_summary.json",
    },
    "api": {
        "host": "127.0.0.1",
        "port": 8765,
    },
}


def _merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: str | Path | None = None) -> GuardConfig:
    root_dir = PROJECT_ROOT
    overlay = read_json(resolve_path(root_dir, config_path)) if config_path else {}
    merged = _merge(DEFAULT_CONFIG, overlay)
    return GuardConfig(
        root_dir=root_dir,
        project_name=str(merged["project_name"]),
        truth_store_path=resolve_path(root_dir, merged["truth_store_path"]),
        verification=VerificationConfig(**dict(merged["verification"])),
        policy=PolicyConfig(**dict(merged["policy"])),
        output=OutputConfig(
            default_jsonl_output=resolve_path(root_dir, merged["output"]["default_jsonl_output"]),
            default_summary_output=resolve_path(root_dir, merged["output"]["default_summary_output"]),
        ),
        api=ApiConfig(**dict(merged["api"])),
    )
