from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from halludomainbench.schemas import ExtractedLink
from halludomainbench.validators import LinkValidator, TemporaryError


class _FakeResponse:
    def __init__(self, status: int, url: str) -> None:
        self.status = status
        self.url = url

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, status: int, url: str) -> None:
        self._status = status
        self._url = url

    def get(self, *args, **kwargs):
        return _FakeResponse(self._status, self._url)


class ValidatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_validate_link_marks_unresolved_domains_as_dead(self) -> None:
        validator = LinkValidator(
            concurrency_limit=5,
            proxy_url="",
            request_timeout_sec=1.0,
            allow_direct=True,
            allow_proxy_fallback=False,
            enable_domain_intel=False,
            use_dns_resolver=False,
            use_rdap=False,
            rdap_timeout_sec=1.0,
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
            enable_domain_intel=False,
            use_dns_resolver=False,
            use_rdap=False,
            rdap_timeout_sec=1.0,
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

    async def test_check_http_status_treats_429_as_unknown_not_live(self) -> None:
        validator = LinkValidator(
            concurrency_limit=5,
            proxy_url="",
            request_timeout_sec=1.0,
            allow_direct=True,
            allow_proxy_fallback=False,
            enable_domain_intel=False,
            use_dns_resolver=False,
            use_rdap=False,
            rdap_timeout_sec=1.0,
        )

        result = await validator.check_http_status(
            session=_FakeSession(status=429, url="https://example.com"),
            url="https://example.com",
            proxy=None,
        )

        self.assertEqual(result["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
