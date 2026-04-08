from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from halludomainbench.schemas import ExtractedLink
from halludomainbench.validators import LinkValidator, TemporaryError


class ValidatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_validate_link_marks_unresolved_domains_as_dead(self) -> None:
        validator = LinkValidator(
            concurrency_limit=5,
            proxy_url="",
            request_timeout_sec=1.0,
            allow_direct=True,
            allow_proxy_fallback=False,
        )
        validator.verify_dns_hint = AsyncMock(return_value=False)
        validator.check_http_status = AsyncMock(side_effect=TemporaryError("lookup failed"))

        evidence = await validator.validate_link(
            session=object(),
            link=ExtractedLink(
                raw="https://not-a-real-domain.invalid",
                url="https://not-a-real-domain.invalid",
                domain="not-a-real-domain.invalid",
                source_field="response",
                position=1,
            ),
        )

        self.assertEqual(evidence.result, "dead")
        self.assertEqual(evidence.reason, "DNS Unresolved")
        self.assertFalse(evidence.dns_resolved)

    async def test_validate_link_keeps_network_failures_as_unknown_when_dns_exists(self) -> None:
        validator = LinkValidator(
            concurrency_limit=5,
            proxy_url="",
            request_timeout_sec=1.0,
            allow_direct=True,
            allow_proxy_fallback=False,
        )
        validator.verify_dns_hint = AsyncMock(return_value=True)
        validator.check_http_status = AsyncMock(side_effect=TemporaryError("timeout"))

        evidence = await validator.validate_link(
            session=object(),
            link=ExtractedLink(
                raw="https://www.python.org",
                url="https://www.python.org",
                domain="www.python.org",
                source_field="response",
                position=1,
            ),
        )

        self.assertEqual(evidence.result, "unknown")
        self.assertEqual(evidence.reason, "Connection Failed")
        self.assertTrue(evidence.dns_resolved)


if __name__ == "__main__":
    unittest.main()
