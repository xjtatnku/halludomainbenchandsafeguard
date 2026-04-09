from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from halludomainbench.starter_assets import (
    EXPANSION10_MODELS,
    MAIN5_MODELS,
    PAIRWISE_ABLATIONS,
    build_experiment_configs,
    build_model_registry_bundle,
    build_default_validation_profiles_bundle,
    build_starter_dataset_bundles,
    build_starter_truth_bundle,
    summarize_truth_bundle,
    write_starter_assets,
)


class StarterAssetsTests(unittest.TestCase):
    def test_truth_bundle_has_expected_coverage(self) -> None:
        truth_bundle = build_starter_truth_bundle()
        summary = summarize_truth_bundle(truth_bundle)

        self.assertEqual(summary["entity_count"], 26)
        self.assertEqual(summary["by_industry"]["tech"], 5)
        self.assertEqual(summary["by_industry"]["finance"], 3)
        self.assertGreaterEqual(summary["by_entry_type"]["homepage"], 26)
        self.assertGreaterEqual(summary["by_entry_type"]["login"], 10)

    def test_dataset_bundles_are_bilingual_and_split_by_profile(self) -> None:
        bundles = build_starter_dataset_bundles()

        self.assertEqual(len(bundles["core"]["records"]), 200)
        self.assertEqual(len(bundles["stress"]["records"]), 108)
        self.assertEqual(len(bundles["open"]["records"]), 24)
        self.assertEqual(len(bundles["full"]["records"]), 332)

        core_languages = {record["language"] for record in bundles["core"]["records"]}
        full_styles = {record["prompt_style"] for record in bundles["full"]["records"]}
        self.assertEqual(core_languages, {"en", "zh"})
        self.assertTrue({"direct", "cautious", "urgent", "noisy", "colloquial"}.issubset(full_styles))

        single_target_missing = [
            record
            for record in bundles["full"]["records"]
            if record["evaluation_mode"] == "single_target" and not record.get("expected_entity")
        ]
        self.assertEqual(single_target_missing, [])

    def test_experiment_configs_cover_main_and_ablation_lineups(self) -> None:
        configs = build_experiment_configs()

        main_config = configs["configs/experiments/main5.core.v1.json"]
        self.assertEqual(main_config["model_selection"]["lineup"], "main5")
        self.assertEqual(main_config["validation_profile"], "baseline_http")
        self.assertTrue(main_config["dataset_path"].endswith("halludomainbench.core.v1.json"))

        for pair_name, models in PAIRWISE_ABLATIONS.items():
            config = configs[f"configs/experiments/ablation.{pair_name}.core.v1.json"]
            self.assertEqual(config["model_selection"]["lineup"], pair_name)
            self.assertEqual(config["validation_profile"], "baseline_http")

    def test_model_registry_bundle_exposes_main_and_expansion_lineups(self) -> None:
        bundle = build_model_registry_bundle()
        self.assertEqual(bundle["lineups"]["main5"], MAIN5_MODELS)
        self.assertEqual(bundle["lineups"]["expansion10"], EXPANSION10_MODELS)
        self.assertGreaterEqual(len(bundle["models"]), 10)

    def test_validation_profile_bundle_exposes_staged_profiles(self) -> None:
        bundle = build_default_validation_profiles_bundle(version="0.4.0")
        self.assertIn("baseline_http", bundle["profiles"])
        self.assertIn("dns_enriched", bundle["profiles"])
        self.assertIn("rdap_curated", bundle["profiles"])
        self.assertTrue(bundle["profiles"]["rdap_curated"]["use_rdap"])

    def test_write_starter_assets_materializes_all_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_map = write_starter_assets(root)

            self.assertTrue(output_map["truth"].exists())
            self.assertTrue(output_map["dataset_core"].exists())
            self.assertTrue(output_map["dataset_stress"].exists())
            self.assertTrue(output_map["dataset_open"].exists())
            self.assertTrue(output_map["dataset_full"].exists())
            self.assertTrue(output_map["taxonomy"].exists())
            self.assertTrue(output_map["model_lineups"].exists())
            self.assertTrue(output_map["model_registry"].exists())
            self.assertTrue(output_map["validation_profiles"].exists())
            self.assertTrue((root / "configs/experiments/main5.core.v1.json").exists())
            self.assertTrue((root / "configs/experiments/ablation.kimi_mode.core.v1.json").exists())


if __name__ == "__main__":
    unittest.main()
