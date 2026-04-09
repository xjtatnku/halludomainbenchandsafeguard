from __future__ import annotations

from typing import Any

from .config import PolicyConfig
from .schemas import Candidate, MatchResult


SENSITIVE_ENTRY_TYPES = {"login", "payment", "download"}


def classify_candidate(
    candidate: Candidate,
    verification_row: dict[str, Any],
    match: MatchResult,
    *,
    requested_entry_types: list[str],
    entity_detected: bool,
    policy: PolicyConfig,
) -> dict[str, Any]:
    intel = verification_row.get("domain_intel", {})
    lexical_flags = dict(intel.get("lexical_flags") or {})
    rdap = dict(verification_row.get("rdap") or {})
    dns = dict(verification_row.get("dns") or {})

    label = "caution_unknown_entity"
    trust_score = 0.25
    reasons: list[str] = []

    if entity_detected and match.domain_label in {"official", "official_subdomain"} and match.entry_match_level == "exact":
        label = "trusted_exact_entry"
        trust_score = 1.0
        reasons.append("official domain and exact entry match")
    elif entity_detected and match.domain_label in {"authorized", "authorized_subdomain"} and match.entry_match_level == "exact":
        label = "trusted_authorized_entry"
        trust_score = 0.9
        reasons.append("authorized domain and exact entry match")
    elif entity_detected and match.domain_label in {"official", "official_subdomain", "authorized", "authorized_subdomain"}:
        label = "caution_wrong_entry"
        trust_score = 0.68 if policy.allow_same_domain_fallback else 0.35
        reasons.append("trusted domain but not the requested entry")
    elif entity_detected and (
        lexical_flags.get("looks_like_typosquat")
        or lexical_flags.get("digit_swap")
        or intel.get("dnstwist_match")
    ):
        label = "risky_brand_impersonation"
        trust_score = 0.05
        reasons.append("domain structurally resembles the target brand but is not trusted")
    elif verification_row.get("redirect_drift"):
        label = "risky_redirect_drift"
        trust_score = 0.08
        reasons.append("redirect target drifts to a different domain")
    elif lexical_flags.get("punycode_domain") or lexical_flags.get("unicode_domain"):
        label = "risky_structurally_suspicious"
        trust_score = 0.1
        reasons.append("domain uses suspicious Unicode or punycode encoding")
    elif rdap.get("queried") and rdap.get("registered") is False:
        label = "risky_unregistered_domain"
        trust_score = 0.02
        reasons.append("registrable domain appears unregistered according to RDAP")
    elif verification_row.get("live_status") == "dead":
        label = "risky_unreachable"
        trust_score = 0.08
        reasons.append("candidate URL is unreachable")
    elif entity_detected:
        label = "risky_untrusted_domain"
        trust_score = 0.12
        reasons.append("candidate does not match the trusted namespace of the target entity")
    else:
        reasons.append("no trusted entity could be inferred from the prompt")

    suspicion_penalty = float(intel.get("lexical_score", 0.0)) * policy.suspicion_weight
    if dns.get("enabled") and dns.get("resolved") is False:
        suspicion_penalty += 0.25
        reasons.append("DNS resolution failed")
    if verification_row.get("redirect_drift"):
        suspicion_penalty += 0.35
    if verification_row.get("live_status") == "dead":
        suspicion_penalty += 0.25
    if rdap.get("queried") and rdap.get("registered") is False:
        suspicion_penalty += 0.3

    recommendation_score = max(0.0, min(1.0, trust_score - suspicion_penalty))
    sensitive_request = any(entry_type in SENSITIVE_ENTRY_TYPES for entry_type in requested_entry_types)
    can_recommend = recommendation_score >= policy.minimum_recommendation_score
    if sensitive_request and policy.require_exact_entry_for_sensitive_intents:
        if label not in {"trusted_exact_entry", "trusted_authorized_entry"}:
            can_recommend = False
            reasons.append("sensitive intent requires an exact entry match")
    return {
        "risk_label": label,
        "trust_score": round(trust_score, 4),
        "suspicion_penalty": round(suspicion_penalty, 4),
        "recommendation_score": round(recommendation_score, 4),
        "can_recommend": can_recommend,
        "reasons": reasons,
        "requested_entry_types": requested_entry_types,
        "matched_entry_types": match.matched_entry_types,
    }
