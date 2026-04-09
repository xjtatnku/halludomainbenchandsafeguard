from __future__ import annotations

from typing import Any


MAIN5_MODELS = [
    "Qwen/Qwen3.5-397B-A17B",
    "deepseek-ai/DeepSeek-V3.2",
    "baidu/ERNIE-4.5-300B-A47B",
    "moonshotai/Kimi-K2-Instruct-0905",
    "zai-org/GLM-4.6",
]

EXPANSION10_MODELS = [
    *MAIN5_MODELS,
    "moonshotai/Kimi-K2-Thinking",
    "Pro/deepseek-ai/DeepSeek-R1",
    "Pro/zai-org/GLM-5",
    "Qwen/Qwen3.5-35B-A3B",
    "tencent/Hunyuan-A13B-Instruct",
]

PAIRWISE_ABLATIONS = {
    "kimi_mode": ["moonshotai/Kimi-K2-Instruct-0905", "moonshotai/Kimi-K2-Thinking"],
    "deepseek_reasoning": ["deepseek-ai/DeepSeek-V3.2", "Pro/deepseek-ai/DeepSeek-R1"],
    "qwen_scale": ["Qwen/Qwen3.5-397B-A17B", "Qwen/Qwen3.5-35B-A3B"],
    "glm_generation": ["zai-org/GLM-4.6", "Pro/zai-org/GLM-5"],
}


def outputs_for(prefix: str) -> dict[str, str]:
    root = f"data/experiments/{prefix}"
    return {
        "raw_responses": f"{root}/response/model_real_outputs.jsonl",
        "validated_responses": f"{root}/response/verified_links.jsonl",
        "scored_responses": f"{root}/response/scored_links.jsonl",
        "legacy_verification_report_csv": f"{root}/response/verification_report.csv",
        "legacy_dead_links_csv": f"{root}/response/verification_report_dead.csv",
        "candidate_report_csv": f"{root}/reports/candidate_report.csv",
        "response_report_csv": f"{root}/reports/response_report.csv",
        "summary_by_model_csv": f"{root}/reports/model_summary.csv",
        "summary_by_domain_csv": f"{root}/reports/domain_summary.csv",
        "summary_by_intent_csv": f"{root}/reports/intent_summary.csv",
        "summary_by_scenario_csv": f"{root}/reports/scenario_summary.csv",
        "summary_by_risk_label_csv": f"{root}/reports/risk_label_summary.csv",
    }


def build_model_registry_bundle(*, version: str) -> dict[str, Any]:
    return {
        "version": version,
        "provider": "siliconflow",
        "updated_at": "2026-04-09",
        "models": [
            {
                "model_id": model_id,
                "provider": "siliconflow",
                "label": model_id.split("/")[-1],
                "family": model_id.split("/", maxsplit=1)[0].replace("Pro", "pro").lower(),
                "tags": sorted(
                    {
                        *(["main5"] if model_id in MAIN5_MODELS else []),
                        *(["expansion10"] if model_id in EXPANSION10_MODELS else []),
                    }
                ),
            }
            for model_id in EXPANSION10_MODELS
        ],
        "lineups": {
            "main5": MAIN5_MODELS,
            "expansion10": EXPANSION10_MODELS,
            **PAIRWISE_ABLATIONS,
        },
    }


def build_validation_profiles_bundle(*, version: str) -> dict[str, Any]:
    return {
        "version": version,
        "updated_at": "2026-04-09",
        "notes": (
            "Stage validation evidence gradually. Use baseline_http while the truth store is still expanding, "
            "dns_enriched when official/authorized coverage is stable, and rdap_curated only after the focused "
            "high-risk truth bundle has been manually reviewed."
        ),
        "profiles": {
            "baseline_http": {
                "concurrency_limit": 80,
                "request_timeout_sec": 12.0,
                "batch_size": 300,
                "proxy_url": "http://127.0.0.1:7890",
                "allow_direct": True,
                "allow_proxy_fallback": True,
                "source_fields": ["response"],
                "enable_domain_intel": True,
                "use_dns_resolver": False,
                "use_rdap": False,
                "rdap_timeout_sec": 4.0,
            },
            "dns_enriched": {
                "concurrency_limit": 60,
                "request_timeout_sec": 12.0,
                "batch_size": 180,
                "proxy_url": "http://127.0.0.1:7890",
                "allow_direct": True,
                "allow_proxy_fallback": True,
                "source_fields": ["response"],
                "enable_domain_intel": True,
                "use_dns_resolver": True,
                "use_rdap": False,
                "rdap_timeout_sec": 4.0,
            },
            "rdap_curated": {
                "concurrency_limit": 36,
                "request_timeout_sec": 14.0,
                "batch_size": 100,
                "proxy_url": "http://127.0.0.1:7890",
                "allow_direct": True,
                "allow_proxy_fallback": True,
                "source_fields": ["response"],
                "enable_domain_intel": True,
                "use_dns_resolver": True,
                "use_rdap": True,
                "rdap_timeout_sec": 4.5,
            },
        },
    }


def build_experiment_configs(*, truth_path: str) -> dict[str, dict[str, Any]]:
    base_collection = {
        "workers": 4,
        "sleep_sec": 1.2,
        "max_retries": 4,
        "temperature": 0.0,
        "max_tokens": 768,
        "timeout_sec": 240.0,
        "resume": False,
        "max_prompts": 0,
        "system_prompt": "",
        "api_env_var": "SILICONFLOW_API_KEY",
    }
    base_validation = {
        "concurrency_limit": 80,
        "request_timeout_sec": 12.0,
        "batch_size": 300,
        "proxy_url": "http://127.0.0.1:7890",
        "allow_direct": True,
        "allow_proxy_fallback": True,
        "source_fields": ["response"],
    }

    configs: dict[str, dict[str, Any]] = {
        "configs/experiments/main5.core.v1.json": {
            "project_name": "HalluDomainBench-Main5-Core",
            "dataset_path": "data/datasets/halludomainbench.core.v1.json",
            "ground_truth_path": truth_path,
            "model_registry_path": "configs/models.siliconflow.v1.json",
            "model_selection": {"lineup": "main5"},
            "outputs": outputs_for("main5_core"),
            "collection": base_collection,
            "validation": base_validation,
            "validation_profile_path": "configs/validation_profiles.v1.json",
            "validation_profile": "baseline_http",
            "metadata": {
                "lineup": "main5",
                "pricing_checked_at": "2026-03-30",
                "pricing_source": "https://siliconflow.cn/pricing",
                "dataset_split": "core",
            },
        },
        "configs/experiments/main5.full.v1.json": {
            "project_name": "HalluDomainBench-Main5-Full",
            "dataset_path": "data/datasets/halludomainbench.full.v1.json",
            "ground_truth_path": truth_path,
            "model_registry_path": "configs/models.siliconflow.v1.json",
            "model_selection": {"lineup": "main5"},
            "outputs": outputs_for("main5_full"),
            "collection": base_collection,
            "validation": base_validation,
            "validation_profile_path": "configs/validation_profiles.v1.json",
            "validation_profile": "baseline_http",
            "metadata": {
                "lineup": "main5",
                "pricing_checked_at": "2026-03-30",
                "pricing_source": "https://siliconflow.cn/pricing",
                "dataset_split": "full",
            },
        },
    }

    for pair_name, models in PAIRWISE_ABLATIONS.items():
        configs[f"configs/experiments/ablation.{pair_name}.core.v1.json"] = {
            "project_name": f"HalluDomainBench-Ablation-{pair_name}",
            "dataset_path": "data/datasets/halludomainbench.core.v1.json",
            "ground_truth_path": truth_path,
            "model_registry_path": "configs/models.siliconflow.v1.json",
            "model_selection": {"lineup": pair_name},
            "outputs": outputs_for(f"ablation_{pair_name}"),
            "collection": base_collection,
            "validation": base_validation,
            "validation_profile_path": "configs/validation_profiles.v1.json",
            "validation_profile": "baseline_http",
            "metadata": {
                "lineup": "paired_ablation",
                "pair_name": pair_name,
                "pricing_checked_at": "2026-03-30",
                "pricing_source": "https://siliconflow.cn/pricing",
                "dataset_split": "core",
            },
        }
    return configs
