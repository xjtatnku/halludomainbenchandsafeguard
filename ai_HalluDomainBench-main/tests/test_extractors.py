from __future__ import annotations

import unittest

from halludomainbench.extractors import extract_links_from_fields, extract_links_from_text


class ExtractorTests(unittest.TestCase):
    def test_extract_links_from_text_prefers_https_and_keeps_positions(self) -> None:
        text = (
            "Use [official](https://www.python.org/downloads/) or "
            "visit http://www.python.org/downloads/ and docs.python.org/3/."
        )

        links = extract_links_from_text(text, "response")

        self.assertEqual(len(links), 2)
        self.assertEqual(links[0].url, "https://www.python.org/downloads")
        self.assertEqual(links[0].domain, "www.python.org")
        self.assertEqual(links[0].position, 1)
        self.assertEqual(links[1].url, "http://docs.python.org/3")
        self.assertEqual(links[1].domain, "docs.python.org")
        self.assertEqual(links[1].position, 2)

    def test_extract_links_from_fields_respects_selected_fields(self) -> None:
        payload = {
            "response": "Official: https://www.python.org/",
            "reasoning_content": "Ignore https://example.com/ because it is hidden reasoning.",
        }

        links = extract_links_from_fields(payload, ("response",))

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].domain, "www.python.org")
        self.assertEqual(links[0].source_field, "response")

    def test_extract_links_strips_markdown_and_cjk_annotations(self) -> None:
        text = (
            "Use https://www.icbc.com.cn**（中国境内）或 "
            "https://global.alipay.com/**（针对境外用户） and "
            "https://www.facebook.com` for reference."
        )

        links = extract_links_from_text(text, "response")

        self.assertEqual([link.domain for link in links], ["www.icbc.com.cn", "global.alipay.com", "www.facebook.com"])

    def test_extract_links_ignores_file_like_tokens(self) -> None:
        text = "Do not use alert.htm or setup.exe, but use https://www.icbc.com.cn/ICBC/."

        links = extract_links_from_text(text, "response")

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].domain, "www.icbc.com.cn")


if __name__ == "__main__":
    unittest.main()
