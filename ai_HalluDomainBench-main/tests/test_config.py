from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from halludomainbench.config import load_config
from halludomainbench.utils import PROJECT_ROOT


class ConfigTests(unittest.TestCase):
    def test_load_config_applies_validation_profile_then_local_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_path = root / "config.json"
            profiles_path = root / "validation_profiles.json"

            profiles_path.write_text(
                json.dumps(
                    {
                        "profiles": {
                            "dns_enriched": {
                                "concurrency_limit": 20,
                                "use_dns_resolver": True,
                                "use_rdap": False,
                                "batch_size": 90,
                                "request_timeout_sec": 10.0,
                            }
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            config_path.write_text(
                json.dumps(
                    {
                        "project_name": "Test",
                        "dataset_path": "new_dataset.json",
                        "ground_truth_path": "data/ground_truth/entities.sample.json",
                        "validation_profile_path": str(profiles_path),
                        "validation_profile": "dns_enriched",
                        "validation": {
                            "batch_size": 33
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config.validation_profile, "dns_enriched")
        self.assertTrue(config.validation.use_dns_resolver)
        self.assertFalse(config.validation.use_rdap)
        self.assertEqual(config.validation.concurrency_limit, 20)
        self.assertEqual(config.validation.batch_size, 33)

    def test_load_config_normalizes_api_env_vars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "project_name": "Test",
                        "dataset_path": "new_dataset.json",
                        "ground_truth_path": "data/ground_truth/entities.sample.json",
                        "collection": {
                            "api_env_vars": ["SILICONFLOW_API_KEY", "BAIDU_QIANFAN_API_KEY", "SILICONFLOW_API_KEY"]
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config.collection.api_env_vars, ("SILICONFLOW_API_KEY", "BAIDU_QIANFAN_API_KEY"))

    def test_load_config_resolves_dataset_overlay_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "project_name": "Test",
                        "dataset_path": "new_dataset.json",
                        "dataset_overlay_path": "data/overlays/new_dataset.overlay.json",
                        "ground_truth_path": "data/ground_truth/entities.sample.json",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config.dataset_overlay_path, PROJECT_ROOT / "data/overlays/new_dataset.overlay.json")

    def test_load_config_resolves_ground_truth_overlay_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "project_name": "Test",
                        "dataset_path": "new_dataset.json",
                        "ground_truth_path": "data/ground_truth/entities.sample.json",
                        "ground_truth_overlay_paths": [
                            "data/ground_truth/entities.extra.json",
                            "data/ground_truth/entities.gov.json",
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(
            config.ground_truth_overlay_paths,
            (
                PROJECT_ROOT / "data/ground_truth/entities.extra.json",
                PROJECT_ROOT / "data/ground_truth/entities.gov.json",
            ),
        )


if __name__ == "__main__":
    unittest.main()
