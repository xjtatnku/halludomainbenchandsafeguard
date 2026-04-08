from __future__ import annotations

import argparse

from halludomainbench.config import load_config
from halludomainbench.pipeline import run_full_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full HalluDomainBench pipeline")
    parser.add_argument("--config", default="configs/benchmark.default.json")
    parser.add_argument("--max-prompts", type=int, default=None)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--sleep-sec", type=float, default=None)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.max_prompts is not None:
        config.collection.max_prompts = args.max_prompts
    if args.workers is not None:
        config.collection.workers = args.workers
    if args.sleep_sec is not None:
        config.collection.sleep_sec = args.sleep_sec
    config.collection.resume = args.resume

    try:
        summary = run_full_benchmark(config)
    except Exception as exc:
        print(f"HalluDomainBench pipeline failed: {exc}")
        return 1
    print("HalluDomainBench pipeline completed.")
    print(summary)
    print(f"- Raw responses: {config.outputs.raw_responses}")
    print(f"- Validated responses: {config.outputs.validated_responses}")
    print(f"- Scored responses: {config.outputs.scored_responses}")
    print(f"- Candidate report: {config.outputs.candidate_report_csv}")
    print(f"- Response report: {config.outputs.response_report_csv}")
    print(f"- Model summary: {config.outputs.summary_by_model_csv}")
    print(f"- Scenario summary: {config.outputs.summary_by_scenario_csv}")
    print(f"- Risk label summary: {config.outputs.summary_by_risk_label_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
