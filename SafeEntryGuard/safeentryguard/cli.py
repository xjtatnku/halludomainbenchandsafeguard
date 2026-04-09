from __future__ import annotations

import argparse
from pathlib import Path

from .api import serve
from .config import load_config
from .guard import SafeEntryGuard


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SafeEntryGuard CLI")
    parser.add_argument("--config", default="configs/guard.default.json", help="Path to the guard config JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_truth = subparsers.add_parser("inspect-truth", help="Inspect the configured truth store")
    inspect_truth.add_argument("--truth", type=Path, default=None)

    filter_one = subparsers.add_parser("filter-one", help="Filter a single prompt-response pair")
    filter_one.add_argument("--prompt", required=True)
    filter_one.add_argument("--response", default="")
    filter_one.add_argument("--response-file", type=Path, default=None)
    filter_one.add_argument("--expected-entity", default="")
    filter_one.add_argument("--entry-type", action="append", default=[])

    filter_jsonl = subparsers.add_parser("filter-jsonl", help="Filter a JSONL file of model outputs")
    filter_jsonl.add_argument("--input", type=Path, required=True)
    filter_jsonl.add_argument("--dataset", type=Path, default=None)
    filter_jsonl.add_argument("--output", type=Path, default=None)
    filter_jsonl.add_argument("--summary", type=Path, default=None)
    filter_jsonl.add_argument("--limit", type=int, default=0)

    serve_parser = subparsers.add_parser("serve", help="Run the minimal SafeEntryGuard Web API")
    serve_parser.add_argument("--host", default="")
    serve_parser.add_argument("--port", type=int, default=0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)
    if args.command == "inspect-truth" and args.truth:
        config.truth_store_path = (config.root_dir / args.truth).resolve() if not args.truth.is_absolute() else args.truth
    guard = SafeEntryGuard(config)

    if args.command == "inspect-truth":
        print(guard.inspect_truth())
        return 0

    if args.command == "filter-one":
        response = args.response
        if args.response_file:
            response = Path(args.response_file).read_text(encoding="utf-8")
        result = guard.filter_answer(
            prompt=args.prompt,
            response=response,
            expected_entity=args.expected_entity,
            requested_entry_types=list(args.entry_type or []),
        )
        print(result)
        return 0

    if args.command == "filter-jsonl":
        output_path = args.output or config.output.default_jsonl_output
        summary_path = args.summary or config.output.default_summary_output
        summary = guard.filter_jsonl(
            input_path=args.input,
            output_path=output_path,
            dataset_path=args.dataset,
            summary_path=summary_path,
            limit=args.limit,
        )
        print(summary)
        return 0

    if args.command == "serve":
        host = str(args.host or config.api.host)
        port = int(args.port or config.api.port)
        serve(guard, host=host, port=port)
        return 0

    parser.error(f"Unhandled command: {args.command}")
    return 2


def main_entry() -> None:
    raise SystemExit(main())
