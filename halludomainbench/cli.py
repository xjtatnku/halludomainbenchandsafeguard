from __future__ import annotations

import argparse
from pathlib import Path

from .config import BenchmarkConfig, load_config
from .dataset import load_prompt_records, summarize_prompts, write_dataset_bundle_template
from .dataset_variants import derive_dataset_subset
from .legacy_migration import write_migrated_legacy_dataset
from .legacy_truth_assets import write_legacy330_highrisk_truth_bundle
from .pipeline import collect_responses, generate_reports, run_full_benchmark, score_responses, verify_responses
from .starter_assets import write_starter_assets
from .taxonomy import write_taxonomy_template
from .truth import GroundTruthIndex, summarize_truth_index, write_truth_template
from .utils import read_jsonl


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
    if getattr(args, "max_tokens", None) is not None:
        config.collection.max_tokens = args.max_tokens
    if getattr(args, "timeout_sec", None) is not None:
        config.collection.timeout_sec = args.timeout_sec
    if getattr(args, "max_retries", None) is not None:
        config.collection.max_retries = args.max_retries


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
    collect_parser.add_argument("--max-tokens", type=int, default=None)
    collect_parser.add_argument("--timeout-sec", type=float, default=None)
    collect_parser.add_argument("--max-retries", type=int, default=None)

    verify_parser = subparsers.add_parser("verify", help="Extract and validate domains or URLs from responses")
    verify_parser.add_argument("--input", type=Path, default=None)
    verify_parser.add_argument("--output", type=Path, default=None)

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

    inspect_parser = subparsers.add_parser("inspect-dataset", help="Print dataset summary")
    inspect_parser.add_argument("--dataset", type=Path, default=None)

    inspect_truth_parser = subparsers.add_parser("inspect-truth", help="Print truth-store summary")
    inspect_truth_parser.add_argument("--truth", type=Path, default=None)

    truth_parser = subparsers.add_parser("bootstrap-truth", help="Write a ground-truth template")
    truth_parser.add_argument("--output", type=Path, default=Path("data/ground_truth/entities.template.json"))

    dataset_parser = subparsers.add_parser("bootstrap-dataset", help="Write a benchmark dataset bundle template")
    dataset_parser.add_argument("--output", type=Path, default=Path("data/datasets/halludomainbench.template.json"))

    taxonomy_parser = subparsers.add_parser("bootstrap-taxonomy", help="Write a prompt/scenario taxonomy template")
    taxonomy_parser.add_argument("--output", type=Path, default=Path("data/taxonomy/scenario_taxonomy.template.json"))

    starter_parser = subparsers.add_parser(
        "bootstrap-starter-assets",
        help="Write starter truth, benchmark datasets, and experiment configs",
    )
    starter_parser.add_argument("--root", type=Path, default=Path("."))

    legacy_truth_parser = subparsers.add_parser(
        "bootstrap-legacy330-highrisk-truth",
        help="Write a focused truth bundle for the legacy330 high-risk targeted subset",
    )
    legacy_truth_parser.add_argument("--root", type=Path, default=Path("."))
    legacy_truth_parser.add_argument("--output", type=Path, default=Path("data/ground_truth/entities.legacy330.highrisk.v1.json"))

    migrate_parser = subparsers.add_parser(
        "migrate-legacy-dataset",
        help="Upgrade an old prompt-only dataset into the richer benchmark schema",
    )
    migrate_parser.add_argument("--input", type=Path, required=True)
    migrate_parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/datasets/legacy.migrated.json"),
    )
    migrate_parser.add_argument("--dataset-name", type=str, default="HalluDomainBench Legacy Migrated")
    migrate_parser.add_argument("--dataset-version", type=str, default="0.3.0")

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
        summary = summarize_prompts(load_prompt_records(dataset_path))
        print(summary)
        return 0

    if args.command == "inspect-truth":
        truth_path = _resolve_optional_path(config.root_dir, args.truth) or config.ground_truth_path
        summary = summarize_truth_index(GroundTruthIndex.load(truth_path))
        print(summary)
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

    if args.command == "bootstrap-starter-assets":
        root_dir = _resolve_optional_path(config.root_dir, args.root) or config.root_dir
        output_map = write_starter_assets(root_dir)
        print("Wrote starter assets:")
        for key, value in sorted(output_map.items()):
            print(f"- {key}: {value}")
        return 0

    if args.command == "bootstrap-legacy330-highrisk-truth":
        root_dir = _resolve_optional_path(config.root_dir, args.root) or config.root_dir
        output_path = _resolve_optional_path(config.root_dir, args.output) or args.output
        written = write_legacy330_highrisk_truth_bundle(root_dir, output_path=output_path)
        print(f"Wrote legacy330 high-risk truth bundle -> {written}")
        return 0

    if args.command == "migrate-legacy-dataset":
        input_path = _resolve_optional_path(config.root_dir, args.input) or args.input
        output_path = _resolve_optional_path(config.root_dir, args.output) or args.output
        bundle = write_migrated_legacy_dataset(
            input_path,
            output_path,
            dataset_name=args.dataset_name,
            dataset_version=args.dataset_version,
        )
        print(f"Wrote migrated dataset -> {output_path}")
        print(f"Records: {len(bundle.get('records', []))}")
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

    parser.error(f"Unhandled command: {args.command}")
    return 2


def main_entry() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main())
