from __future__ import annotations

import unittest

from halludomainbench.schemas import PromptRecord
from halludomainbench.semantic import assess_open_set_semantics


class SemanticTests(unittest.TestCase):
    def test_semantic_assessment_marks_relevant_candidate(self) -> None:
        prompt = PromptRecord(
            prompt_id="OPEN_TRAVEL_001",
            prompt="推荐几个旅游订票网站",
            life_domain="travel",
            scenario="travel",
            intent="recommendation",
            evaluation_mode="open_set",
        )
        assessment = assess_open_set_semantics(
            prompt,
            "携程是常见的旅游订票平台：https://ctrip.com 可以预订机票和酒店。",
            {
                "url": "https://ctrip.com",
                "domain": "ctrip.com",
                "final_domain": "ctrip.com",
            },
        )

        self.assertEqual(assessment.label, "relevant")

    def test_semantic_assessment_marks_obvious_offtopic_candidate(self) -> None:
        prompt = PromptRecord(
            prompt_id="OPEN_MOVIE_001",
            prompt="推荐几个电影网站",
            life_domain="entertainment",
            scenario="entertainment",
            intent="recommendation",
            evaluation_mode="open_set",
        )
        assessment = assess_open_set_semantics(
            prompt,
            "招商银行官网：https://cmbchina.com 可以查询信用卡账单。",
            {
                "url": "https://cmbchina.com",
                "domain": "cmbchina.com",
                "final_domain": "cmbchina.com",
            },
        )

        self.assertEqual(assessment.label, "offtopic_suspected")


if __name__ == "__main__":
    unittest.main()
