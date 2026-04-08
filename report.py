from __future__ import annotations

import argparse
from pathlib import Path

from halludomainbench.config import load_config
from halludomainbench.pipeline import generate_reports
from halludomainbench.utils import read_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description="Legacy reporting entrypoint for HalluDomainBench")
    parser.add_argument("--config", default="configs/benchmark.default.json")
    parser.add_argument("--validated-input", type=Path, default=None)
    parser.add_argument("--scored-input", type=Path, default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    validated_rows = None
    scored_rows = None
    if args.validated_input is not None:
        validated_path = (config.root_dir / args.validated_input).resolve() if not args.validated_input.is_absolute() else args.validated_input
        validated_rows = read_jsonl(validated_path)
    if args.scored_input is not None:
        scored_path = (config.root_dir / args.scored_input).resolve() if not args.scored_input.is_absolute() else args.scored_input
        scored_rows = read_jsonl(scored_path)

    generate_reports(config, scored_rows=scored_rows, validated_rows=validated_rows)
    print("Reports generated.")
    print(f"- Legacy verification report: {config.outputs.legacy_verification_report_csv}")
    print(f"- Legacy dead-only report: {config.outputs.legacy_dead_links_csv}")
    print(f"- Candidate report: {config.outputs.candidate_report_csv}")
    print(f"- Response report: {config.outputs.response_report_csv}")
    print(f"- Model summary: {config.outputs.summary_by_model_csv}")
    print(f"- Scenario summary: {config.outputs.summary_by_scenario_csv}")
    print(f"- Risk label summary: {config.outputs.summary_by_risk_label_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
