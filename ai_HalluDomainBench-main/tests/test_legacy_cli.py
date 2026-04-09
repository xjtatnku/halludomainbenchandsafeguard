from __future__ import annotations

import unittest
from unittest.mock import patch

from halludomainbench.legacy_cli import (
    run_legacy_collect,
    run_legacy_report,
    run_legacy_run,
    run_legacy_verify,
)


class LegacyCliTests(unittest.TestCase):
    def test_run_legacy_collect_forwards_to_modern_collect(self) -> None:
        with patch("halludomainbench.legacy_cli.cli_main", return_value=0) as mocked:
            result = run_legacy_collect(["--config", "demo.json", "--max-prompts", "3", "--resume"])

        self.assertEqual(result, 0)
        mocked.assert_called_once_with(["--config", "demo.json", "collect", "--max-prompts", "3", "--resume"])

    def test_run_legacy_verify_forwards_reasoning_flag(self) -> None:
        with patch("halludomainbench.legacy_cli.cli_main", return_value=0) as mocked:
            result = run_legacy_verify(["--config", "demo.json", "--include-reasoning"])

        self.assertEqual(result, 0)
        mocked.assert_called_once_with(["--config", "demo.json", "verify", "--include-reasoning"])

    def test_run_legacy_report_forwards_paths(self) -> None:
        with patch("halludomainbench.legacy_cli.cli_main", return_value=0) as mocked:
            result = run_legacy_report(
                ["--config", "demo.json", "--validated-input", "v.jsonl", "--scored-input", "s.jsonl"]
            )

        self.assertEqual(result, 0)
        mocked.assert_called_once_with(
            ["--config", "demo.json", "report", "--validated-input", "v.jsonl", "--scored-input", "s.jsonl"]
        )

    def test_run_legacy_run_forwards_sampling_flags(self) -> None:
        with patch("halludomainbench.legacy_cli.cli_main", return_value=0) as mocked:
            result = run_legacy_run(
                [
                    "--config",
                    "demo.json",
                    "--max-prompts",
                    "5",
                    "--temperature",
                    "0",
                    "--top-p",
                    "0.95",
                ]
            )

        self.assertEqual(result, 0)
        mocked.assert_called_once_with(
            ["--config", "demo.json", "run", "--max-prompts", "5", "--temperature", "0.0", "--top-p", "0.95"]
        )


if __name__ == "__main__":
    unittest.main()
