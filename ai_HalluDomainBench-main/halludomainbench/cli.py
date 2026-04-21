from __future__ import annotations

import argparse
from pathlib import Path

from .config import BenchmarkConfig, load_config
from .dataset import load_prompt_records, summarize_prompts, validate_prompt_records, write_dataset_bundle_template
from .dataset_variants import deduplicate_dataset, derive_dataset_subset
from .models import load_model_registry
from .pipeline import collect_responses, generate_reports, run_full_benchmark, score_responses, verify_responses
from .taxonomy import write_taxonomy_template
from .truth import GroundTruthIndex, summarize_truth_index, write_truth_template
from .utils import read_jsonl
from .validation_profiles import load_validation_profiles


def _resolve_optional_path(root, path: Path | None) -> Path | None:
    if path is None:
        return None
    if path.is_absolute():
        return path
    return (root / path).resolve()


def _apply_common_overrides(config: BenchmarkConfig, args: argparse.Namespace) -> None:
    if getattr(args, "max_prompts", None) is not None:
        config.collection.max_prompts = args.max_prompts
    if getattr(args, "resume", None) is not None:
        config.collection.resume = args.resume
    if getattr(args, "workers", None) is not None:
        config.collection.workers = args.workers
    if getattr(args, "sleep_sec", None) is not None:
        config.collection.sleep_sec = args.sleep_sec
    if getattr(args, "system_prompt", None) is not None:
        config.collection.system_prompt = args.system_prompt
    if getattr(args, "temperature", None) is not None:
        config.collection.temperature = args.temperature
    if getattr(args, "top_p", None) is not None:
        config.collection.top_p = args.top_p
    if getattr(args, "presence_penalty", None) is not None:
        config.collection.presence_penalty = args.presence_penalty
    if getattr(args, "frequency_penalty", None) is not None:
        config.collection.frequency_penalty = args.frequency_penalty
    if getattr(args, "max_tokens", None) is not None:
        config.collection.max_tokens = args.max_tokens
    if getattr(args, "timeout_sec", None) is not None:
        config.collection.timeout_sec = args.timeout_sec
    if getattr(args, "max_retries", None) is not None:
        config.collection.max_retries = args.max_retries
    if getattr(args, "validation_profile", None):
        print(
            "Validation profile overrides should be applied via config files. "
            "Use inspect-validation-profiles to choose a profile and create a dedicated experiment config."
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HalluDomainBench CLI")
    parser.add_argument("--config", default="configs/benchmark.default.json", help="Path to the benchmark config JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="Collect raw model responses")
    collect_parser.add_argument("--output", type=Path, default=None)
    collect_parser.add_argument("--max-prompts", type=int, default=None)
    collect_parser.add_argument("--resume", action="store_true")
    collect_parser.add_argument("--workers", type=int, default=None)
    collect_parser.add_argument("--sleep-sec", type=float, default=None)
    collect_parser.add_argument("--system-prompt", type=str, default=None)
    collect_parser.add_argument("--temperature", type=float, default=None)
    collect_parser.add_argument("--top-p", type=float, default=None)
    collect_parser.add_argument("--presence-penalty", type=float, default=None)
    collect_parser.add_argument("--frequency-penalty", type=float, default=None)
    collect_parser.add_argument("--max-tokens", type=int, default=None)
    collect_parser.add_argument("--timeout-sec", type=float, default=None)
    collect_parser.add_argument("--max-retries", type=int, default=None)

    verify_parser = subparsers.add_parser("verify", help="Extract and validate domains or URLs from responses")
    verify_parser.add_argument("--input", type=Path, default=None)
    verify_parser.add_argument("--output", type=Path, default=None)
    verify_parser.add_argument("--include-reasoning", action="store_true")

    score_parser = subparsers.add_parser("score", help="Score validated domains against the truth store")
    score_parser.add_argument("--input", type=Path, default=None)
    score_parser.add_argument("--output", type=Path, default=None)

    report_parser = subparsers.add_parser("report", help="Generate compatibility and benchmark reports")
    report_parser.add_argument("--validated-input", type=Path, default=None)
    report_parser.add_argument("--scored-input", type=Path, default=None)

    run_parser = subparsers.add_parser("run", help="Run collect + verify + score + report")
    run_parser.add_argument("--max-prompts", type=int, default=None)
    run_parser.add_argument("--resume", action="store_true")
    run_parser.add_argument("--workers", type=int, default=None)
    run_parser.add_argument("--sleep-sec", type=float, default=None)
    run_parser.add_argument("--temperature", type=float, default=None)
    run_parser.add_argument("--top-p", type=float, default=None)
    run_parser.add_argument("--presence-penalty", type=float, default=None)
    run_parser.add_argument("--frequency-penalty", type=float, default=None)
    run_parser.add_argument("--max-tokens", type=int, default=None)
    run_parser.add_argument("--timeout-sec", type=float, default=None)
    run_parser.add_argument("--max-retries", type=int, default=None)

    inspect_parser = subparsers.add_parser("inspect-dataset", help="Print dataset summary")
    inspect_parser.add_argument("--dataset", type=Path, default=None)

    validate_dataset_parser = subparsers.add_parser("validate-dataset", help="Validate the JSON dataset bundle")
    validate_dataset_parser.add_argument("--dataset", type=Path, default=None)

    inspect_truth_parser = subparsers.add_parser("inspect-truth", help="Print truth-store summary")
    inspect_truth_parser.add_argument("--truth", type=Path, default=None)

    inspect_models_parser = subparsers.add_parser("inspect-models", help="Inspect a model registry and lineup selection")
    inspect_models_parser.add_argument("--registry", type=Path, default=Path("configs/models.registry.v2.json"))
    inspect_models_parser.add_argument("--lineup", type=str, default="")

    inspect_validation_parser = subparsers.add_parser(
        "inspect-validation-profiles",
        help="Inspect available staged validation profiles",
    )
    inspect_validation_parser.add_argument("--profiles", type=Path, default=Path("configs/validation_profiles.v1.json"))

    truth_parser = subparsers.add_parser("bootstrap-truth", help="Write a ground-truth template")
    truth_parser.add_argument("--output", type=Path, default=Path("data/ground_truth/entities.template.json"))

    dataset_parser = subparsers.add_parser("bootstrap-dataset", help="Write a benchmark dataset bundle template")
    dataset_parser.add_argument("--output", type=Path, default=Path("data/datasets/halludomainbench.template.json"))

    taxonomy_parser = subparsers.add_parser("bootstrap-taxonomy", help="Write a prompt/scenario taxonomy template")
    taxonomy_parser.add_argument("--output", type=Path, default=Path("data/taxonomy/scenario_taxonomy.template.json"))

    subset_parser = subparsers.add_parser(
        "derive-dataset-subset",
        help="Create a filtered benchmark dataset bundle from an existing dataset",
    )
    subset_parser.add_argument("--input", type=Path, required=True)
    subset_parser.add_argument("--output", type=Path, required=True)
    subset_parser.add_argument("--dataset-name", type=str, required=True)
    subset_parser.add_argument("--dataset-version", type=str, default="0.3.0")
    subset_parser.add_argument("--evaluation-mode", action="append", default=[])
    subset_parser.add_argument("--intent", action="append", default=[])
    subset_parser.add_argument("--require-expected-entity", action="store_true")

    dedup_parser = subparsers.add_parser(
        "deduplicate-dataset",
        help="Write a deduplicated JSON dataset without modifying the original file",
    )
    dedup_parser.add_argument("--input", type=Path, required=True)
    dedup_parser.add_argument("--output", type=Path, required=True)
    dedup_parser.add_argument("--dedup-key", type=str, default="prompt")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)

    if args.command == "collect":
        _apply_common_overrides(config, args)
        output_path = _resolve_optional_path(config.root_dir, args.output)
        rows = collect_responses(config, output_path=output_path)
        print(f"Collected {len(rows)} responses -> {output_path or config.outputs.raw_responses}")
        return 0

    if args.command == "verify":
        input_path = _resolve_optional_path(config.root_dir, args.input)
        output_path = _resolve_optional_path(config.root_dir, args.output)
        if getattr(args, "include_reasoning", False):
            config.validation.source_fields = ("response", "reasoning_content")
        rows = verify_responses(config, input_path=input_path, output_path=output_path)
        print(f"Validated {len(rows)} responses -> {output_path or config.outputs.validated_responses}")
        return 0

    if args.command == "score":
        input_path = _resolve_optional_path(config.root_dir, args.input)
        output_path = _resolve_optional_path(config.root_dir, args.output)
        rows = score_responses(config, input_path=input_path, output_path=output_path)
        print(f"Scored {len(rows)} responses -> {output_path or config.outputs.scored_responses}")
        return 0

    if args.command == "report":
        validated_path = _resolve_optional_path(config.root_dir, args.validated_input)
        scored_path = _resolve_optional_path(config.root_dir, args.scored_input)
        validated_rows = read_jsonl(validated_path) if validated_path else None
        scored_rows = read_jsonl(scored_path) if scored_path else None
        generate_reports(config, scored_rows=scored_rows, validated_rows=validated_rows)
        print("Reports generated.")
        return 0

    if args.command == "run":
        _apply_common_overrides(config, args)
        summary = run_full_benchmark(config)
        print(summary)
        return 0

    if args.command == "inspect-dataset":
        dataset_path = _resolve_optional_path(config.root_dir, args.dataset) or config.dataset_path
        summary = summarize_prompts(load_prompt_records(dataset_path, overlay_path=config.dataset_overlay_path))
        print(summary)
        return 0

    if args.command == "validate-dataset":
        dataset_path = _resolve_optional_path(config.root_dir, args.dataset) or config.dataset_path
        prompts = load_prompt_records(dataset_path, overlay_path=config.dataset_overlay_path)
        issues = validate_prompt_records(prompts)
        print({"dataset": str(dataset_path), "prompt_count": len(prompts), "issues": issues, "issue_count": len(issues)})
        return 0

    if args.command == "inspect-truth":
        truth_path = _resolve_optional_path(config.root_dir, args.truth) or config.ground_truth_path
        overlay_paths = [] if getattr(args, "truth", None) else list(config.ground_truth_overlay_paths)
        summary = summarize_truth_index(GroundTruthIndex.load_many([truth_path, *overlay_paths]))
        print(summary)
        return 0

    if args.command == "inspect-models":
        registry_path = _resolve_optional_path(config.root_dir, args.registry) or args.registry
        registry = load_model_registry(registry_path)
        specs = registry.select(lineup=args.lineup) if args.lineup else registry.select()
        print(
            {
                "registry": str(registry_path),
                "lineup": args.lineup or "all_enabled",
                "count": len(specs),
                "models": [spec.to_dict() for spec in specs],
            }
        )
        return 0

    if args.command == "inspect-validation-profiles":
        profiles_path = _resolve_optional_path(config.root_dir, args.profiles) or args.profiles
        profiles = load_validation_profiles(profiles_path)
        print({"profiles_path": str(profiles_path), "profiles": profiles})
        return 0

    if args.command == "bootstrap-truth":
        output_path = _resolve_optional_path(config.root_dir, args.output)
        write_truth_template(output_path)
        print(f"Wrote ground-truth template -> {output_path}")
        return 0

    if args.command == "bootstrap-dataset":
        output_path = _resolve_optional_path(config.root_dir, args.output)
        write_dataset_bundle_template(output_path)
        print(f"Wrote dataset template -> {output_path}")
        return 0

    if args.command == "bootstrap-taxonomy":
        output_path = _resolve_optional_path(config.root_dir, args.output)
        write_taxonomy_template(output_path)
        print(f"Wrote taxonomy template -> {output_path}")
        return 0

    if args.command == "derive-dataset-subset":
        input_path = _resolve_optional_path(config.root_dir, args.input) or args.input
        output_path = _resolve_optional_path(config.root_dir, args.output) or args.output
        bundle = derive_dataset_subset(
            input_path,
            output_path,
            dataset_name=args.dataset_name,
            dataset_version=args.dataset_version,
            evaluation_modes=set(args.evaluation_mode or []) or None,
            intents=set(args.intent or []) or None,
            require_expected_entity=bool(args.require_expected_entity),
        )
        print(f"Wrote derived dataset -> {output_path}")
        print(f"Records: {len(bundle.get('records', []))}")
        return 0

    if args.command == "deduplicate-dataset":
        input_path = _resolve_optional_path(config.root_dir, args.input) or args.input
        output_path = _resolve_optional_path(config.root_dir, args.output) or args.output
        summary = deduplicate_dataset(
            input_path,
            output_path,
            dedup_key=args.dedup_key,
        )
        print(summary)
        return 0

    parser.error(f"Unhandled command: {args.command}")
    return 2


def main_entry() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main())
