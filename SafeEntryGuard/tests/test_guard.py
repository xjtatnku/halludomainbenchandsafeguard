from pathlib import Path
import unittest
from unittest.mock import patch

from safeentryguard.config import load_config
from safeentryguard.guard import SafeEntryGuard


def _fake_verify(url: str, **kwargs):
    domain = url.split("//", 1)[-1].split("/", 1)[0]
    final_url = url
    return {
        "url": url,
        "domain": domain,
        "http_status": 200,
        "final_url": final_url,
        "final_domain": domain,
        "live_status": "live",
        "error": "",
        "redirect_drift": False,
        "dns": {"enabled": False, "resolved": None, "records": {}},
        "rdap": {"queried": False, "registered": None},
        "domain_intel": {
            "domain": domain,
            "registrable_domain": domain,
            "lexical_flags": {
                "unicode_domain": False,
                "punycode_domain": False,
                "digit_swap": "githu8" in domain,
                "long_subdomain_chain": False,
                "many_hyphens": "-" in domain,
                "suspicious_keyword": "secure" in domain,
                "looks_like_typosquat": "githu8" in domain,
            },
            "similarity_to_official": 0.89 if "githu8" in domain else 1.0,
            "similar_official_domain": "github.com",
            "dnstwist_match": "githu8" in domain,
            "lexical_score": 0.4 if "githu8" in domain else 0.0,
        },
    }


class GuardTests(unittest.TestCase):
    def setUp(self) -> None:
        config = load_config(Path("configs/guard.default.json"))
        config.truth_store_path = Path("data/truth/entities.sample.json").resolve()
        self.guard = SafeEntryGuard(config)

    @patch("safeentryguard.guard.verify_candidate", side_effect=_fake_verify)
    def test_prefers_exact_login_entry(self, _mock_verify) -> None:
        result = self.guard.filter_answer(
            prompt="GitHub login page",
            response="Use https://github.com/login and docs.github.com if you need docs.",
        )
        self.assertFalse(result["rejected"])
        self.assertEqual(result["recommended"]["candidate"]["normalized_url"], "https://github.com/login")

    @patch("safeentryguard.guard.verify_candidate", side_effect=_fake_verify)
    def test_rejects_only_typosquat_for_sensitive_intent(self, _mock_verify) -> None:
        result = self.guard.filter_answer(
            prompt="GitHub login page",
            response="Try https://githu8.com/login for GitHub login.",
        )
        self.assertTrue(result["rejected"])

    @patch("safeentryguard.guard.verify_candidate", side_effect=_fake_verify)
    def test_filter_rows_uses_meta_intent_when_dataset_missing(self, _mock_verify) -> None:
        rows = [
            {
                "model": "demo",
                "prompt_id": "P001",
                "response": "Use https://github.com/login",
                "meta": {"intent": "login_entry"},
                "prompt": "GitHub login page",
            }
        ]
        filtered_rows, summary = self.guard.filter_rows(rows)
        self.assertEqual(summary["accepted_count"], 1)
        self.assertEqual(filtered_rows[0]["recommended_label"], "trusted_exact_entry")


if __name__ == "__main__":
    unittest.main()
