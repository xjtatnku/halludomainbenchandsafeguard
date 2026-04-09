import unittest

from safeentryguard.extractors import extract_candidates


class ExtractorTests(unittest.TestCase):
    def test_extracts_urls_and_domains(self) -> None:
        text = "Use https://github.com/login or docs.github.com for documentation."
        candidates = extract_candidates(text)
        urls = [candidate.normalized_url for candidate in candidates]
        self.assertIn("https://github.com/login", urls)
        self.assertIn("https://docs.github.com/", urls)


if __name__ == "__main__":
    unittest.main()
