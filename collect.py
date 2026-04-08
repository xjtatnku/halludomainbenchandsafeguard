from __future__ import annotations

import argparse
from pathlib import Path

from halludomainbench.config import load_config
from halludomainbench.pipeline import collect_responses


def main() -> int:
    parser = argparse.ArgumentParser(description="Legacy collect entrypoint for HalluDomainBench")
    parser.add_argument("--config", default="configs/benchmark.default.json")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--system-prompt", type=str, default=None)
    parser.add_argument("--max-prompts", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--timeout-sec", type=float, default=None)
    parser.add_argument("--sleep-sec", type=float, default=None)
    parser.add_argument("--max-retries", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    if args.output is not None:
        config.outputs.raw_responses = (config.root_dir / args.output).resolve() if not args.output.is_absolute() else args.output
    if args.system_prompt is not None:
        config.collection.system_prompt = args.system_prompt
    if args.max_prompts is not None:
        config.collection.max_prompts = args.max_prompts
    if args.temperature is not None:
        config.collection.temperature = args.temperature
    if args.max_tokens is not None:
        config.collection.max_tokens = args.max_tokens
    if args.timeout_sec is not None:
        config.collection.timeout_sec = args.timeout_sec
    if args.sleep_sec is not None:
        config.collection.sleep_sec = args.sleep_sec
    if args.max_retries is not None:
        config.collection.max_retries = args.max_retries
    if args.workers is not None:
        config.collection.workers = args.workers
    config.collection.resume = args.resume

    try:
        rows = collect_responses(config, output_path=config.outputs.raw_responses)
    except Exception as exc:
        print(f"Collection failed: {exc}")
        return 1
    print(f"Collected {len(rows)} rows -> {config.outputs.raw_responses}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
