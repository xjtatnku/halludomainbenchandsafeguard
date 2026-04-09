from __future__ import annotations

import argparse
from pathlib import Path

from .cli import main as cli_main


def _append_optional_path(argv: list[str], flag: str, value: Path | None) -> None:
    if value is not None:
        argv.extend([flag, str(value)])


def _append_optional_value(argv: list[str], flag: str, value: str | int | float | None) -> None:
    if value is not None:
        argv.extend([flag, str(value)])


def run_legacy_collect(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Legacy collect entrypoint for HalluDomainBench")
    parser.add_argument("--config", default="configs/benchmark.default.json")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--system-prompt", type=str, default=None)
    parser.add_argument("--max-prompts", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--presence-penalty", type=float, default=None)
    parser.add_argument("--frequency-penalty", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--timeout-sec", type=float, default=None)
    parser.add_argument("--sleep-sec", type=float, default=None)
    parser.add_argument("--max-retries", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args(argv)

    forwarded = ["--config", args.config, "collect"]
    _append_optional_path(forwarded, "--output", args.output)
    _append_optional_value(forwarded, "--system-prompt", args.system_prompt)
    _append_optional_value(forwarded, "--max-prompts", args.max_prompts)
    _append_optional_value(forwarded, "--temperature", args.temperature)
    _append_optional_value(forwarded, "--top-p", args.top_p)
    _append_optional_value(forwarded, "--presence-penalty", args.presence_penalty)
    _append_optional_value(forwarded, "--frequency-penalty", args.frequency_penalty)
    _append_optional_value(forwarded, "--max-tokens", args.max_tokens)
    _append_optional_value(forwarded, "--timeout-sec", args.timeout_sec)
    _append_optional_value(forwarded, "--sleep-sec", args.sleep_sec)
    _append_optional_value(forwarded, "--max-retries", args.max_retries)
    _append_optional_value(forwarded, "--workers", args.workers)
    if args.resume:
        forwarded.append("--resume")
    return cli_main(forwarded)


def run_legacy_verify(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Legacy verification entrypoint for HalluDomainBench")
    parser.add_argument("--config", default="configs/benchmark.default.json")
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--include-reasoning", action="store_true", help="Also validate links emitted in reasoning_content")
    args = parser.parse_args(argv)

    forwarded = ["--config", args.config, "verify"]
    _append_optional_path(forwarded, "--input", args.input)
    _append_optional_path(forwarded, "--output", args.output)
    if args.include_reasoning:
        forwarded.append("--include-reasoning")
    return cli_main(forwarded)


def run_legacy_report(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Legacy reporting entrypoint for HalluDomainBench")
    parser.add_argument("--config", default="configs/benchmark.default.json")
    parser.add_argument("--validated-input", type=Path, default=None)
    parser.add_argument("--scored-input", type=Path, default=None)
    args = parser.parse_args(argv)

    forwarded = ["--config", args.config, "report"]
    _append_optional_path(forwarded, "--validated-input", args.validated_input)
    _append_optional_path(forwarded, "--scored-input", args.scored_input)
    return cli_main(forwarded)


def run_legacy_run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the full HalluDomainBench pipeline")
    parser.add_argument("--config", default="configs/benchmark.default.json")
    parser.add_argument("--max-prompts", type=int, default=None)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--sleep-sec", type=float, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--presence-penalty", type=float, default=None)
    parser.add_argument("--frequency-penalty", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--timeout-sec", type=float, default=None)
    parser.add_argument("--max-retries", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)

    forwarded = ["--config", args.config, "run"]
    _append_optional_value(forwarded, "--max-prompts", args.max_prompts)
    _append_optional_value(forwarded, "--workers", args.workers)
    _append_optional_value(forwarded, "--sleep-sec", args.sleep_sec)
    _append_optional_value(forwarded, "--temperature", args.temperature)
    _append_optional_value(forwarded, "--top-p", args.top_p)
    _append_optional_value(forwarded, "--presence-penalty", args.presence_penalty)
    _append_optional_value(forwarded, "--frequency-penalty", args.frequency_penalty)
    _append_optional_value(forwarded, "--max-tokens", args.max_tokens)
    _append_optional_value(forwarded, "--timeout-sec", args.timeout_sec)
    _append_optional_value(forwarded, "--max-retries", args.max_retries)
    if args.resume:
        forwarded.append("--resume")
    return cli_main(forwarded)
