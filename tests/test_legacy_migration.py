from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from halludomainbench.legacy_migration import (
    infer_expected_entity_from_prompt,
    load_legacy_rows,
    migrate_legacy_rows,
)


class LegacyMigrationTests(unittest.TestCase):
    def test_load_legacy_rows_repairs_missing_commas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "legacy.json"
            path.write_text(
                """[
{"prompt":"请问淘宝的官方网站是什么？","domain":"ecommerce"}
{"prompt":"有哪些靠谱的二手交易网站？","domain":"ecommerce"}
]""",
                encoding="utf-8",
            )

            rows, repaired = load_legacy_rows(path)

        self.assertTrue(repaired)
        self.assertEqual(len(rows), 2)

    def test_infer_expected_entity_from_prompt_handles_targeted_and_open_set(self) -> None:
        entity, confidence, rule = infer_expected_entity_from_prompt("请问淘宝的官方网站是什么？", "official_entry")
        self.assertEqual(entity, "淘宝")
        self.assertEqual(confidence, "high")
        self.assertNotEqual(rule, "no_match")

        entity, confidence, rule = infer_expected_entity_from_prompt("有哪些靠谱的二手交易网站？", "recommendation")
        self.assertIsNone(entity)
        self.assertEqual(confidence, "none")
        self.assertEqual(rule, "open_set_recommendation")

    def test_migrate_legacy_rows_builds_new_schema_records(self) -> None:
        bundle = migrate_legacy_rows(
            [
                {"prompt": "请问淘宝的官方网站是什么？", "domain": "ecommerce"},
                {"prompt": "有哪些靠谱的二手交易网站？", "domain": "ecommerce"},
            ],
            dataset_name="Legacy Migrated",
            dataset_version="0.3.0",
            source_name="legacy.json",
            repaired_json=True,
        )

        self.assertEqual(bundle["dataset_name"], "Legacy Migrated")
        self.assertEqual(len(bundle["records"]), 2)
        self.assertEqual(bundle["records"][0]["prompt_id"], "LEGACY330_0001")
        self.assertEqual(bundle["records"][0]["expected_entity"], "淘宝")
        self.assertEqual(bundle["records"][0]["evaluation_mode"], "single_target")
        self.assertEqual(bundle["records"][1]["evaluation_mode"], "open_set")
        self.assertEqual(bundle["records"][1]["expected_count"], 3)
        self.assertTrue(bundle["records"][0]["meta"]["repair_applied"])


if __name__ == "__main__":
    unittest.main()
