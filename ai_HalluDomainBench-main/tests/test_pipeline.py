from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from halludomainbench.config import BenchmarkConfig, CollectionConfig, OutputConfig, ScoringConfig, ValidationConfig
from halludomainbench.pipeline import filter_rows_for_selected_models, generate_reports


class PipelineTests(unittest.TestCase):
    def test_filter_rows_for_selected_models_ignores_retired_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            outputs = OutputConfig(
                raw_responses=root / "data/response/model_real_outputs.jsonl",
                validated_responses=root / "data/response/verified_links.jsonl",
                scored_responses=root / "data/response/scored_links.jsonl",
                legacy_verification_report_csv=root / "data/response/verification_report.csv",
                legacy_dead_links_csv=root / "data/response/verification_report_dead.csv",
                candidate_report_csv=root / "data/reports/candidate_report.csv",
                response_report_csv=root / "data/reports/response_report.csv",
                summary_by_model_csv=root / "data/reports/model_summary.csv",
                summary_by_domain_csv=root / "data/reports/domain_summary.csv",
                summary_by_intent_csv=root / "data/reports/intent_summary.csv",
                summary_by_scenario_csv=root / "data/reports/scenario_summary.csv",
                summary_by_target_count_csv=root / "data/reports/target_count_summary.csv",
                summary_by_risk_label_csv=root / "data/reports/risk_label_summary.csv",
            )
            config = BenchmarkConfig(
                root_dir=root,
                project_name="HalluDomainBench",
                dataset_path=root / "dataset.json",
                dataset_overlay_path=None,
                ground_truth_path=root / "truth.json",
                ground_truth_overlay_paths=(),
                models=["model.active", "model.new"],
                outputs=outputs,
                collection=CollectionConfig(),
                validation=ValidationConfig(),
                scoring=ScoringConfig(),
            )

            rows = [
                {"model": "model.active", "prompt_id": "A"},
                {"model": "model.retired", "prompt_id": "A"},
                {"model": "model.new", "prompt_id": "B"},
            ]

            filtered = filter_rows_for_selected_models(rows, config)

        self.assertEqual([row["model"] for row in filtered], ["model.active", "model.new"])

    def test_generate_reports_clears_stale_scored_outputs_when_no_scored_rows_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            outputs = OutputConfig(
                raw_responses=root / "data/response/model_real_outputs.jsonl",
                validated_responses=root / "data/response/verified_links.jsonl",
                scored_responses=root / "data/response/scored_links.jsonl",
                legacy_verification_report_csv=root / "data/response/verification_report.csv",
                legacy_dead_links_csv=root / "data/response/verification_report_dead.csv",
                candidate_report_csv=root / "data/reports/candidate_report.csv",
                response_report_csv=root / "data/reports/response_report.csv",
                summary_by_model_csv=root / "data/reports/model_summary.csv",
                summary_by_domain_csv=root / "data/reports/domain_summary.csv",
                summary_by_intent_csv=root / "data/reports/intent_summary.csv",
                summary_by_scenario_csv=root / "data/reports/scenario_summary.csv",
                summary_by_target_count_csv=root / "data/reports/target_count_summary.csv",
                summary_by_risk_label_csv=root / "data/reports/risk_label_summary.csv",
            )
            config = BenchmarkConfig(
                root_dir=root,
                project_name="HalluDomainBench",
                dataset_path=root / "dataset.json",
                dataset_overlay_path=None,
                ground_truth_path=root / "truth.json",
                ground_truth_overlay_paths=(),
                models=[],
                outputs=outputs,
                collection=CollectionConfig(),
                validation=ValidationConfig(),
                scoring=ScoringConfig(),
            )

            outputs.candidate_report_csv.parent.mkdir(parents=True, exist_ok=True)
            outputs.candidate_report_csv.write_text("stale-data", encoding="utf-8")
            outputs.summary_by_model_csv.write_text("stale-data", encoding="utf-8")
            outputs.response_report_csv.write_text("stale-data", encoding="utf-8")
            outputs.summary_by_target_count_csv.write_text("stale-data", encoding="utf-8")

            generate_reports(config, scored_rows=[], validated_rows=[])

            self.assertEqual(outputs.candidate_report_csv.read_text(encoding="utf-8-sig"), "")
            self.assertEqual(outputs.summary_by_model_csv.read_text(encoding="utf-8-sig"), "")
            self.assertEqual(outputs.response_report_csv.read_text(encoding="utf-8-sig"), "")
            self.assertEqual(outputs.summary_by_target_count_csv.read_text(encoding="utf-8-sig"), "")


if __name__ == "__main__":
    unittest.main()
