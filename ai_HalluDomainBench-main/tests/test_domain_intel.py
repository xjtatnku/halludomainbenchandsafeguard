from __future__ import annotations

import unittest

from halludomainbench.domain_intel import analyze_domain, registrable_domain_parts


class DomainIntelTests(unittest.TestCase):
    def test_registrable_domain_parts_handles_compound_suffix(self) -> None:
        registrable, suffix = registrable_domain_parts("shop.login.example.co.uk")
        self.assertEqual(registrable, "example.co.uk")
        self.assertEqual(suffix, "co.uk")

    def test_analyze_domain_marks_structural_flags(self) -> None:
        intel = analyze_domain("xn--secure-paypal-7vb-login-2026.com", use_dns_resolver=False, use_rdap=False)

        self.assertEqual(intel.registrable_domain, "xn--secure-paypal-7vb-login-2026.com")
        self.assertTrue(intel.uses_punycode)
        self.assertIn("punycode_domain", intel.lexical_flags)
        self.assertGreater(intel.lexical_score, 0.0)


if __name__ == "__main__":
    unittest.main()
