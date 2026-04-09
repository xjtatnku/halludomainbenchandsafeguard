from __future__ import annotations

from pathlib import Path

from .utils import write_json


INTENT_TO_ENTRY_TYPES: dict[str, tuple[str, ...]] = {
    "official_entry": ("homepage",),
    "login_entry": ("login", "account", "signin"),
    "payment_entry": ("payment", "billing", "wallet"),
    "download_entry": ("download", "installer", "sdk", "docs"),
    "support_entry": ("support", "help_center", "customer_service"),
    "resource_navigation": ("resource",),
    "recommendation": (),
    "unknown": (),
}


PROMPT_FAMILY_DEFAULTS: dict[str, str] = {
    "official_entry": "brand_lookup",
    "login_entry": "credential_entry",
    "payment_entry": "transaction_entry",
    "download_entry": "software_access",
    "support_entry": "support_navigation",
    "resource_navigation": "resource_navigation",
    "recommendation": "open_recommendation",
    "unknown": "generic_query",
}


ENTRY_TYPE_RISK_LEVELS: dict[str, str] = {
    "homepage": "medium",
    "login": "high",
    "signin": "high",
    "account": "high",
    "payment": "critical",
    "billing": "critical",
    "wallet": "critical",
    "download": "high",
    "installer": "high",
    "sdk": "medium",
    "docs": "medium",
    "support": "medium",
    "help_center": "medium",
    "customer_service": "medium",
    "resource": "low",
}


def default_expected_entry_types(intent: str) -> list[str]:
    return list(INTENT_TO_ENTRY_TYPES.get(intent, ()))


def infer_evaluation_mode(*, intent: str, expected_entity: str | None) -> str:
    if expected_entity:
        return "single_target"
    if intent in {"official_entry", "login_entry", "payment_entry", "download_entry", "support_entry"}:
        return "single_target"
    return "open_set"


def default_prompt_family(intent: str) -> str:
    return PROMPT_FAMILY_DEFAULTS.get(intent, PROMPT_FAMILY_DEFAULTS["unknown"])


def write_taxonomy_template(path: Path) -> None:
    template = {
        "version": "0.2.0",
        "evaluation_modes": {
            "single_target": "Targeted lookup tasks that should resolve to a specific entity and entry point.",
            "open_set": "Open-world recommendation or discovery tasks where multiple domains may be acceptable.",
        },
        "life_domains": {
            "ecommerce": ["marketplace", "brand_store", "shopping_assistant"],
            "finance": ["banking", "wallet", "payment", "loan"],
            "government": ["public_service", "identity", "transport"],
            "healthcare": ["hospital", "insurance", "vaccination"],
            "tech": ["developer_tool", "download", "documentation"],
            "travel": ["booking", "transport", "lodging"],
            "social": ["messaging", "community", "creator"],
            "entertainment": ["streaming", "gaming", "media"],
        },
        "intents": {
            intent: {
                "expected_entry_types": list(entry_types),
                "default_prompt_family": default_prompt_family(intent),
            }
            for intent, entry_types in INTENT_TO_ENTRY_TYPES.items()
        },
        "entry_types": ENTRY_TYPE_RISK_LEVELS,
    }
    write_json(path, template)
