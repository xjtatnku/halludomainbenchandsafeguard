from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from halludomainbench.dataset_variants import deduplicate_dataset


class DatasetVariantTests(unittest.TestCase):
    def test_deduplicate_dataset_preserves_original_shape_for_list_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "legacy_list.json"
            output_path = root / "legacy_list.dedup.json"
            input_path.write_text(
                json.dumps(
                    [
                        {"prompt": "Recommend 3 movie sites", "target_count": 3},
                        {"prompt": "Recommend 3 movie sites", "target_count": 3},
                        {"prompt": "Recommend 5 movie sites", "target_count": 5},
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            summary = deduplicate_dataset(input_path, output_path, dedup_key="prompt")
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["input_count"], 3)
        self.assertEqual(summary["output_count"], 2)
        self.assertEqual(summary["removed_count"], 1)
        self.assertIsInstance(payload, list)
        self.assertEqual(len(payload), 2)

    def test_deduplicate_dataset_updates_bundle_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "bundle.json"
            output_path = root / "bundle.dedup.json"
            input_path.write_text(
                json.dumps(
                    {
                        "dataset_name": "Demo",
                        "dataset_version": "0.1.0",
                        "records": [
                            {"prompt_id": "A", "prompt": "One"},
                            {"prompt_id": "B", "prompt": "One"},
                            {"prompt_id": "C", "prompt": "Two"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            summary = deduplicate_dataset(input_path, output_path, dedup_key="prompt")
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["removed_count"], 1)
        self.assertEqual(len(payload["records"]), 2)
        self.assertEqual(payload["metadata"]["dedup"]["dedup_key"], "prompt")
        self.assertEqual(payload["metadata"]["dedup"]["output_count"], 2)


if __name__ == "__main__":
    unittest.main()
