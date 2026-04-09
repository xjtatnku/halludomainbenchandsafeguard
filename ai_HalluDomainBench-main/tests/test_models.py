from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from halludomainbench.models import load_model_registry, resolve_model_selection


class ModelRegistryTests(unittest.TestCase):
    def test_load_model_registry_and_select_lineup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            registry_path = Path(tmp_dir) / "models.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "models": [
                            {"model_id": "model.a", "family": "alpha", "tags": ["main5"]},
                            {"model_id": "model.b", "family": "beta", "tags": ["main5", "reasoning"]},
                            {"model_id": "model.c", "enabled": False, "tags": ["main10"]},
                        ],
                        "lineups": {
                            "main5": ["model.a", "model.b"],
                            "main10": ["model.a", "model.b", "model.c"],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            registry = load_model_registry(registry_path)
            specs = registry.select(lineup="main5")

        self.assertEqual([spec.model_id for spec in specs], ["model.a", "model.b"])
        self.assertEqual(specs[0].family, "alpha")

    def test_resolve_model_selection_prefers_registry_lineup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            registry_path = root / "models.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "models": [
                            {"model_id": "model.a"},
                            {"model_id": "model.b"},
                            {"model_id": "model.c"},
                        ],
                        "lineups": {"main5": ["model.a", "model.b"]},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            model_ids, specs, resolved_registry, lineup = resolve_model_selection(
                root_dir=root,
                models_payload=["fallback.model"],
                registry_path="models.json",
                selection={"lineup": "main5"},
            )

        self.assertEqual(model_ids, ["model.a", "model.b"])
        self.assertEqual([spec.model_id for spec in specs], ["model.a", "model.b"])
        self.assertEqual(lineup, "main5")
        self.assertEqual(resolved_registry, registry_path.resolve())


if __name__ == "__main__":
    unittest.main()
