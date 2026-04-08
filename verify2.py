from __future__ import annotations

import argparse
from pathlib import Path

from halludomainbench.config import load_config
from halludomainbench.pipeline import verify_responses


def main() -> int:
    parser = argparse.ArgumentParser(description="Legacy verification entrypoint for HalluDomainBench")
    parser.add_argument("--config", default="configs/benchmark.default.json")
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--include-reasoning", action="store_true", help="Also validate links emitted in reasoning_content")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.input is not None:
        config.outputs.raw_responses = (config.root_dir / args.input).resolve() if not args.input.is_absolute() else args.input
    if args.output is not None:
        config.outputs.validated_responses = (config.root_dir / args.output).resolve() if not args.output.is_absolute() else args.output
    if args.include_reasoning:
        config.validation.source_fields = ("response", "reasoning_content")

    rows = verify_responses(
        config,
        input_path=config.outputs.raw_responses,
        output_path=config.outputs.validated_responses,
    )
    print(f"Validated {len(rows)} rows -> {config.outputs.validated_responses}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
