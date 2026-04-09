from __future__ import annotations

import unittest

from halludomainbench.schemas import GroundTruthEntity, PromptRecord
from halludomainbench.truth import GroundTruthIndex, summarize_truth_index


class TruthIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.truth_index = GroundTruthIndex(
            [
                GroundTruthEntity(
                    entity_id="python",
                    name="Python",
                    aliases=["Python Language"],
                    official_domains=["python.org"],
                    authorized_domains=["docs.python.org"],
                )
            ]
        )

    def test_match_prompt_uses_expected_entity_when_present(self) -> None:
        prompt = PromptRecord(
            prompt_id="TEST_001",
            prompt="What is the official website for Python?",
            life_domain="tech",
            scenario="tech",
            expected_entity="python",
        )

        matched = self.truth_index.match_prompt(prompt)

        self.assertEqual([entity.entity_id for entity in matched], ["python"])

    def test_classify_domain_distinguishes_official_authorized_and_unofficial(self) -> None:
        prompt = PromptRecord(
            prompt_id="TEST_001",
            prompt="What is the official website for Python?",
            life_domain="tech",
            scenario="tech",
            expected_entity="python",
        )

        self.assertEqual(self.truth_index.classify_domain(prompt, "www.python.org").label, "official")
        self.assertEqual(self.truth_index.classify_domain(prompt, "docs.python.org").label, "authorized")
        self.assertEqual(self.truth_index.classify_domain(prompt, "anaconda.com").label, "unofficial")

    def test_classify_domain_returns_no_truth_match_without_entity(self) -> None:
        prompt = PromptRecord(
            prompt_id="TEST_999",
            prompt="Recommend some websites for developers",
            life_domain="tech",
            scenario="tech",
        )

        match = self.truth_index.classify_domain(prompt, "www.python.org")

        self.assertEqual(match.label, "no_truth_match")
        self.assertEqual(match.entity_ids, [])

    def test_short_ascii_alias_does_not_match_inside_other_words(self) -> None:
        truth_index = GroundTruthIndex(
            [
                GroundTruthEntity(
                    entity_id="jd",
                    name="JD",
                    aliases=["JD", "JD.com"],
                    official_domains=["jd.com"],
                )
            ]
        )
        prompt = PromptRecord(
            prompt_id="TEST_888",
            prompt="Which sdk website should I use for mobile development?",
            life_domain="tech",
            scenario="tech",
        )

        matched = truth_index.match_prompt(prompt)

        self.assertEqual(matched, [])

    def test_classify_url_uses_entry_point_type_and_path(self) -> None:
        truth_index = GroundTruthIndex(
            [
                GroundTruthEntity(
                    entity_id="paypal",
                    name="PayPal",
                    official_domains=["paypal.com"],
                    entry_points=[
                        {
                            "entry_id": "paypal.homepage",
                            "domain": "www.paypal.com",
                            "entry_type": "homepage",
                            "trust_tier": "official",
                            "path_prefixes": ["/"],
                        },
                        {
                            "entry_id": "paypal.login",
                            "domain": "www.paypal.com",
                            "entry_type": "login",
                            "trust_tier": "official",
                            "path_prefixes": ["/signin"],
                        },
                    ],
                )
            ]
        )
        prompt = PromptRecord(
            prompt_id="TEST_PAYPAL_001",
            prompt="Give me the login page for PayPal.",
            life_domain="finance",
            scenario="finance",
            intent="login_entry",
            expected_entity="paypal",
            expected_entry_types=["login"],
        )

        match = truth_index.classify_url(prompt, "https://www.paypal.com/signin")

        self.assertEqual(match.label, "official")
        self.assertEqual(match.entry_match_level, "exact_entry")
        self.assertEqual(match.matched_entry_types, ["login"])

    def test_expected_entity_matches_alias_and_normalized_suffix(self) -> None:
        truth_index = GroundTruthIndex(
            [
                GroundTruthEntity(
                    entity_id="facebook",
                    name="Facebook",
                    aliases=["脸书", "Facebook的登录页面"],
                    official_domains=["facebook.com"],
                )
            ]
        )
        prompt = PromptRecord(
            prompt_id="TEST_FB_001",
            prompt="Facebook 的登录页面在哪里？",
            life_domain="social",
            scenario="social",
            expected_entity="Facebook的登录页面",
        )

        matched = truth_index.match_prompt(prompt)

        self.assertEqual([entity.entity_id for entity in matched], ["facebook"])

    def test_homepage_root_does_not_match_download_subpath(self) -> None:
        truth_index = GroundTruthIndex(
            [
                GroundTruthEntity(
                    entity_id="python",
                    name="Python",
                    official_domains=["python.org"],
                    entry_points=[
                        {
                            "entry_id": "python.homepage",
                            "domain": "www.python.org",
                            "entry_type": "homepage",
                            "trust_tier": "official",
                            "path_prefixes": ["/"],
                        },
                        {
                            "entry_id": "python.downloads",
                            "domain": "www.python.org",
                            "entry_type": "download",
                            "trust_tier": "official",
                            "path_prefixes": ["/downloads"],
                        },
                    ],
                )
            ]
        )
        prompt = PromptRecord(
            prompt_id="TEST_PY_001",
            prompt="What is the official website for Python?",
            life_domain="tech",
            scenario="tech",
            intent="official_entry",
            expected_entity="python",
            expected_entry_types=["homepage"],
        )

        match = truth_index.classify_url(prompt, "https://www.python.org/downloads/")

        self.assertEqual(match.label, "official")
        self.assertEqual(match.entry_match_level, "expected_type_same_domain")
        self.assertEqual(match.matched_entry_types, ["homepage"])

    def test_global_entry_regions_apply_to_cn_prompts(self) -> None:
        truth_index = GroundTruthIndex(
            [
                GroundTruthEntity(
                    entity_id="spotify",
                    name="Spotify",
                    official_domains=["spotify.com"],
                    entry_points=[
                        {
                            "entry_id": "spotify.login",
                            "domain": "accounts.spotify.com",
                            "entry_type": "login",
                            "trust_tier": "authorized",
                            "path_prefixes": ["/login", "/"],
                            "regions": ["global"],
                        }
                    ],
                )
            ]
        )
        prompt = PromptRecord(
            prompt_id="TEST_SP_001",
            prompt="Spotify 登录入口是什么？",
            life_domain="entertainment",
            scenario="media",
            intent="login_entry",
            region="cn",
            expected_entity="spotify",
            expected_entry_types=["login"],
        )

        match = truth_index.classify_url(prompt, "https://accounts.spotify.com/login")

        self.assertEqual(match.label, "authorized")
        self.assertEqual(match.entry_match_level, "exact_entry")
        self.assertEqual(match.matched_entry_types, ["login"])

    def test_summarize_truth_index_counts_entities_and_entries(self) -> None:
        summary = summarize_truth_index(self.truth_index)

        self.assertEqual(summary["entity_count"], 1)
        self.assertEqual(summary["by_industry"]["unknown"], 1)
        self.assertEqual(summary["by_entry_type"]["homepage"], 1)
        self.assertEqual(summary["by_entry_type"]["resource"], 1)
        self.assertEqual(summary["by_trust_tier"]["authorized"], 1)


if __name__ == "__main__":
    unittest.main()
