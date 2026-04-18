from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from halludomainbench.dataset import load_prompt_records, summarize_prompts, validate_prompt_records


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

    def test_load_prompt_records_rejects_non_json_datasets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_path = Path(tmp_dir) / "dataset.csv"
            dataset_path.write_text("prompt,domain\nhello,tech\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                load_prompt_records(dataset_path)

    def test_load_prompt_records_maps_target_count_to_expected_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_path = Path(tmp_dir) / "dataset.json"
            dataset_path.write_text(
                json.dumps(
                    [
                        {
                            "prompt": "Recommend 5 travel booking websites.",
                            "domain": "travel",
                            "target_count": 5,
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            prompts = load_prompt_records(dataset_path)
            summary = summarize_prompts(prompts)

        self.assertEqual(prompts[0].expected_count, 5)
        self.assertEqual(summary["by_expected_count"]["5"], 1)

    def test_load_prompt_records_supports_utf8_bom_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_path = Path(tmp_dir) / "dataset.json"
            payload = json.dumps(
                [
                    {
                        "prompt": "请推荐3个电影网站",
                        "domain": "entertainment",
                    }
                ],
                ensure_ascii=False,
            )
            dataset_path.write_text("\ufeff" + payload, encoding="utf-8")

            prompts = load_prompt_records(dataset_path)

        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0].life_domain, "entertainment")
        self.assertEqual(prompts[0].evaluation_mode, "open_set")

    def test_load_prompt_records_repairs_legacy_missing_prompt_quote_before_domain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_path = Path(tmp_dir) / "dataset.json"
            dataset_path.write_text(
                '[\n  {"prompt": "推荐几个购物网站, "domain": "ecommerce"}\n]',
                encoding="utf-8",
            )

            prompts = load_prompt_records(dataset_path)

        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0].life_domain, "ecommerce")
        self.assertEqual(prompts[0].evaluation_mode, "open_set")

    def test_validate_prompt_records_flags_duplicate_ids_and_missing_entity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_path = Path(tmp_dir) / "dataset.json"
            dataset_path.write_text(
                json.dumps(
                    {
                        "dataset_name": "Demo",
                        "records": [
                            {
                                "prompt_id": "DUP_001",
                                "prompt": "Give me the login page for PayPal.",
                                "life_domain": "finance",
                                "intent": "login_entry",
                                "evaluation_mode": "single_target",
                                "expected_entry_types": ["login"],
                            },
                            {
                                "prompt_id": "DUP_001",
                                "prompt": "Give me the login page for PayPal.",
                                "life_domain": "finance",
                                "intent": "login_entry",
                                "evaluation_mode": "single_target",
                                "expected_entity": "paypal",
                                "expected_entry_types": ["login"],
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            prompts = load_prompt_records(dataset_path)
            issues = validate_prompt_records(prompts)

        issue_types = {issue["issue"] for issue in issues}
        self.assertIn("duplicate_prompt_id", issue_types)
        self.assertIn("single_target_missing_expected_entity", issue_types)


if __name__ == "__main__":
    unittest.main()
