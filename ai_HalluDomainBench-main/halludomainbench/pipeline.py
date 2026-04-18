from __future__ import annotations

import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any

from .config import BenchmarkConfig
from .dataset import index_prompts_by_id, load_prompt_records
from .models import ModelSpec, normalize_model_spec
from .providers import LLMFactory, load_api_keys
from .reporting import write_csv, write_legacy_reports
from .scoring import (
    aggregate_risk_labels,
    aggregate_scored_rows,
    flatten_response_metrics,
    flatten_scored_candidates,
    score_rows,
)
from .truth import GroundTruthIndex
from .utils import append_jsonl, read_jsonl, utc_now_iso, write_jsonl
from .validators import validate_rows


def load_existing_pairs(path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    seen = set()
    for row in read_jsonl(path):
        model = str(row.get("model", "")).strip()
        prompt_id = str(row.get("prompt_id", "")).strip()
        if model and prompt_id:
            seen.add((model, prompt_id))
    return seen


def collect_responses(config: BenchmarkConfig, *, output_path=None) -> list[dict]:
    prompts = load_prompt_records(config.dataset_path)
    if config.collection.max_prompts > 0:
        prompts = prompts[: config.collection.max_prompts]
    model_specs = config.model_specs or [normalize_model_spec(model_name) for model_name in config.models]

    output_file = output_path or config.outputs.raw_responses
    if output_file.exists() and not config.collection.resume:
        output_file.unlink()
    seen = load_existing_pairs(output_file) if config.collection.resume else set()
    api_keys = load_api_keys(config.collection.api_env_var, config.collection.api_key_file)
    if not api_keys.get("SILICONFLOW_API_KEY"):
        raise RuntimeError(
            "Missing API key: set the environment variable "
            f"{config.collection.api_env_var} or populate {config.collection.api_key_file} before running collection."
        )
    client_cache: dict[str, Any] = {}
    lock = Lock()

    def process_one(prompt, model_spec: ModelSpec):
        pair = (model_spec.model_id, prompt.prompt_id)
        with lock:
            if pair in seen:
                return
            seen.add(pair)
            cache_key = model_spec.provider
            if cache_key not in client_cache:
                client_cache[cache_key] = LLMFactory.get_client(model_spec, api_keys)
            client = client_cache[cache_key]

        attempt = 0
        last_error = ""
        response_text = ""
        reasoning_content = ""
        usage = {}
        finish_reason = ""
        request_temperature = config.collection.temperature
        request_top_p = config.collection.top_p
        request_presence_penalty = config.collection.presence_penalty
        request_frequency_penalty = config.collection.frequency_penalty
        request_max_tokens = config.collection.max_tokens
        request_timeout = config.collection.timeout_sec
        request_system_prompt = config.collection.system_prompt
        while attempt <= config.collection.max_retries:
            attempt += 1
            try:
                request_overrides = dict(model_spec.request_overrides)
                request_temperature = float(request_overrides.pop("temperature", config.collection.temperature))
                request_top_p = float(request_overrides.pop("top_p", config.collection.top_p))
                request_presence_penalty = float(
                    request_overrides.pop("presence_penalty", config.collection.presence_penalty)
                )
                request_frequency_penalty = float(
                    request_overrides.pop("frequency_penalty", config.collection.frequency_penalty)
                )
                request_max_tokens = int(request_overrides.pop("max_tokens", config.collection.max_tokens))
                request_timeout = float(request_overrides.pop("timeout_sec", config.collection.timeout_sec))
                request_system_prompt = str(request_overrides.pop("system_prompt", config.collection.system_prompt))
                result = client.chat_completion(
                    model=model_spec.model_id,
                    user_text=prompt.prompt,
                    system_prompt=request_system_prompt,
                    temperature=request_temperature,
                    top_p=request_top_p,
                    presence_penalty=request_presence_penalty,
                    frequency_penalty=request_frequency_penalty,
                    max_tokens=request_max_tokens,
                    timeout_sec=request_timeout,
                    request_overrides=request_overrides,
                )
                response_text = result.get("content", "")
                reasoning_content = result.get("reasoning_content", "")
                usage = result.get("usage", {})
                finish_reason = result.get("finish_reason", "")
                break
            except Exception as exc:
                last_error = str(exc)
                if attempt <= config.collection.max_retries:
                    backoff = min(0.8 * (2 ** (attempt - 1)) + random.random() * 0.35, 10.0)
                    time.sleep(backoff)

        row = {
            "model": model_spec.model_id,
            "prompt_id": prompt.prompt_id,
            "response": response_text,
            "reasoning_content": reasoning_content,
            "created_at": utc_now_iso(),
            "meta": {
                "model_label": model_spec.label or model_spec.model_id,
                "model_family": model_spec.family,
                "model_provider": model_spec.provider,
                "model_tags": model_spec.tags,
                "life_domain": prompt.life_domain,
                "scenario": prompt.scenario,
                "intent": prompt.intent,
                "risk_tier": prompt.risk_tier,
                "language": prompt.language,
                "prompt_style": prompt.prompt_style,
                "ambiguity_level": prompt.ambiguity_level,
                "context_noise": prompt.context_noise,
                "urgency": prompt.urgency,
                "request_overrides": model_spec.request_overrides,
                "sampling": {
                    "temperature": request_temperature,
                    "top_p": request_top_p,
                    "presence_penalty": request_presence_penalty,
                    "frequency_penalty": request_frequency_penalty,
                    "max_tokens": request_max_tokens,
                    "timeout_sec": request_timeout,
                },
                "finish_reason": finish_reason,
                "usage": usage,
                "error": last_error if not response_text else "",
            },
        }

        with lock:
            append_jsonl(output_file, row)

        if config.collection.sleep_sec > 0:
            time.sleep(config.collection.sleep_sec)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=config.collection.workers) as executor:
        futures = [executor.submit(process_one, prompt, model_spec) for prompt in prompts for model_spec in model_specs]
        for future in as_completed(futures):
            future.result()

    return read_jsonl(output_file)


def verify_responses(config: BenchmarkConfig, *, input_path=None, output_path=None) -> list[dict]:
    input_file = input_path or config.outputs.raw_responses
    output_file = output_path or config.outputs.validated_responses
    rows = read_jsonl(input_file)
    validated = validate_rows(
        rows,
        concurrency_limit=config.validation.concurrency_limit,
        proxy_url=config.validation.proxy_url,
        request_timeout_sec=config.validation.request_timeout_sec,
        batch_size=config.validation.batch_size,
        allow_direct=config.validation.allow_direct,
        allow_proxy_fallback=config.validation.allow_proxy_fallback,
        source_fields=config.validation.source_fields,
        enable_domain_intel=config.validation.enable_domain_intel,
        use_dns_resolver=config.validation.use_dns_resolver,
        use_rdap=config.validation.use_rdap,
        rdap_timeout_sec=config.validation.rdap_timeout_sec,
    )
    write_jsonl(output_file, validated)
    return validated


def score_responses(config: BenchmarkConfig, *, input_path=None, output_path=None) -> list[dict]:
    input_file = input_path or config.outputs.validated_responses
    output_file = output_path or config.outputs.scored_responses

    prompts = load_prompt_records(config.dataset_path)
    prompts_by_id = index_prompts_by_id(prompts)
    truth_index = GroundTruthIndex.load(config.ground_truth_path)
    validated_rows = read_jsonl(input_file)
    scored = score_rows(
        validated_rows,
        prompts_by_id=prompts_by_id,
        truth_index=truth_index,
        intent_weights=config.scoring.intent_weights,
        label_weights=config.scoring.label_weights,
        allow_subdomains=config.scoring.allow_subdomains,
        rank_decay=config.scoring.rank_decay,
        suspicion_weight=config.scoring.suspicion_weight,
    )
    write_jsonl(output_file, scored)
    return scored


def generate_reports(config: BenchmarkConfig, *, scored_rows=None, validated_rows=None) -> None:
    if validated_rows is None:
        validated_rows = read_jsonl(config.outputs.validated_responses) if config.outputs.validated_responses.exists() else []
    if scored_rows is None:
        scored_rows = read_jsonl(config.outputs.scored_responses) if config.outputs.scored_responses.exists() else []

    write_legacy_reports(
        validated_rows,
        output_csv=config.outputs.legacy_verification_report_csv,
        dead_only_csv=config.outputs.legacy_dead_links_csv,
    )
    write_csv(config.outputs.candidate_report_csv, flatten_scored_candidates(scored_rows))
    write_csv(config.outputs.response_report_csv, flatten_response_metrics(scored_rows))
    write_csv(config.outputs.summary_by_model_csv, aggregate_scored_rows(scored_rows, "model"))
    write_csv(config.outputs.summary_by_domain_csv, aggregate_scored_rows(scored_rows, "life_domain"))
    write_csv(config.outputs.summary_by_intent_csv, aggregate_scored_rows(scored_rows, "intent"))
    write_csv(config.outputs.summary_by_scenario_csv, aggregate_scored_rows(scored_rows, "scenario"))
    write_csv(config.outputs.summary_by_target_count_csv, aggregate_scored_rows(scored_rows, "target_count"))
    write_csv(config.outputs.summary_by_risk_label_csv, aggregate_risk_labels(scored_rows))


def run_full_benchmark(config: BenchmarkConfig) -> dict[str, int]:
    collected = collect_responses(config)
    validated = verify_responses(config)
    scored = score_responses(config)
    generate_reports(config, scored_rows=scored, validated_rows=validated)
    return {
        "collected": len(collected),
        "validated": len(validated),
        "scored": len(scored),
    }
