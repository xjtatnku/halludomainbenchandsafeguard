from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from halludomainbench.dataset import load_prompt_records, summarize_prompts


class DatasetTests(unittest.TestCase):
    def test_load_prompt_records_normalizes_ids_and_infers_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_path = Path(tmp_dir) / "dataset.json"
            dataset_path.write_text(
                json.dumps(
                    [
                        {
                            "prompt": "What is the official website for Python?",
                            "domain": "tech",
                            "expected_entity": "python",
                        },
                        {
                            "prompt": "Recommend some streaming platforms",
                            "domain": "entertainment",
                        },
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            prompts = load_prompt_records(dataset_path)

        self.assertEqual(prompts[0].prompt_id, "TEST_001")
        self.assertEqual(prompts[0].intent, "official_entry")
        self.assertEqual(prompts[0].language, "en")
        self.assertEqual(prompts[0].expected_entity, "python")
        self.assertEqual(prompts[0].evaluation_mode, "single_target")
        self.assertEqual(prompts[0].expected_entry_types, ["homepage"])

        self.assertEqual(prompts[1].prompt_id, "TEST_002")
        self.assertEqual(prompts[1].intent, "recommendation")
        self.assertEqual(prompts[1].risk_tier, "low")
        self.assertEqual(prompts[1].evaluation_mode, "open_set")

        summary = summarize_prompts(prompts)
        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["by_domain"]["tech"], 1)
        self.assertEqual(summary["by_domain"]["entertainment"], 1)
        self.assertEqual(summary["by_evaluation_mode"]["single_target"], 1)
        self.assertEqual(summary["by_evaluation_mode"]["open_set"], 1)


if __name__ == "__main__":
    unittest.main()
