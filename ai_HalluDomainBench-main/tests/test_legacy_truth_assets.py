from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from halludomainbench.legacy_truth_assets import (
    CURATED_HIGHRISK_ENTITIES,
    build_legacy330_highrisk_truth_bundle,
    write_legacy330_highrisk_truth_bundle,
)
from halludomainbench.truth import GroundTruthIndex
from halludomainbench.utils import read_json, write_json


class LegacyTruthAssetTests(unittest.TestCase):
    def test_build_bundle_merges_base_and_curated_entities(self) -> None:
        base_payload = {
            "entities": [
                {
                    "entity_id": "example",
                    "name": "Example",
                    "official_domains": ["example.com"],
                    "authorized_domains": [],
                    "entry_points": [],
                }
            ]
        }

        bundle = build_legacy330_highrisk_truth_bundle(base_payload)
        entity_ids = {entity["entity_id"] for entity in bundle["entities"]}

        self.assertIn("example", entity_ids)
        self.assertIn("alipay", entity_ids)
        self.assertIn("wechat_pay", entity_ids)
        self.assertEqual(len(entity_ids), len(bundle["entities"]))

    def test_writer_produces_truth_bundle_covering_curated_entities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            base_path = root / "data/ground_truth/entities.starter.v1.json"
            write_json(base_path, {"entities": []})

            output_path = write_legacy330_highrisk_truth_bundle(root)
            bundle = read_json(output_path)
            truth_index = GroundTruthIndex.load(output_path)

        entity_ids = {entity["entity_id"] for entity in bundle["entities"]}
        curated_ids = {entity["entity_id"] for entity in CURATED_HIGHRISK_ENTITIES}

        self.assertTrue(curated_ids.issubset(entity_ids))
        self.assertEqual(len(truth_index.entities), len(bundle["entities"]))


if __name__ == "__main__":
    unittest.main()
