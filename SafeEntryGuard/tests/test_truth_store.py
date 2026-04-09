from pathlib import Path
import unittest

from safeentryguard.truth_store import TruthStore


class TruthStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.truth = TruthStore.load(Path("data/truth/entities.sample.json"))

    def test_infer_entity_from_prompt(self) -> None:
        inference = self.truth.infer_entity("Give me the GitHub login page")
        self.assertIsNotNone(inference)
        assert inference is not None
        self.assertEqual(inference.entity_id, "github")

    def test_infer_requested_entry_type(self) -> None:
        entry_types = self.truth.infer_requested_entry_types("Please provide the Python download page")
        self.assertIn("download", entry_types)

    def test_match_exact_entry(self) -> None:
        entity = self.truth.find_entity("github")
        match = self.truth.match_candidate("https://github.com/login", entity, ["login"])
        self.assertEqual(match.domain_label, "official")
        self.assertEqual(match.entry_match_level, "exact")


if __name__ == "__main__":
    unittest.main()
