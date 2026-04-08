from __future__ import annotations

import asyncio
import re
import socket
from urllib.parse import urlparse

import aiohttp
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .extractors import extract_links_from_fields
from .schemas import ExtractedLink, ValidationEvidence


class DeterministicError(Exception):
    """Non-retryable validation failure."""


class TemporaryError(Exception):
    """Retryable validation failure."""


class LinkValidator:
    def __init__(
        self,
        *,
        concurrency_limit: int,
        proxy_url: str,
        request_timeout_sec: float,
        allow_direct: bool,
        allow_proxy_fallback: bool,
    ) -> None:
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self.proxy_url = proxy_url.strip()
        self.request_timeout_sec = request_timeout_sec
        self.allow_direct = allow_direct
        self.allow_proxy_fallback = allow_proxy_fallback and bool(self.proxy_url)

    async def verify_dns_hint(self, domain: str) -> bool:
        if not domain or len(domain) > 255:
            return False
        clean_domain = domain.split(":", maxsplit=1)[0].strip("./\\:\"'()[]{} ")
        if not clean_domain or not re.match(r"^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$", clean_domain):
            return False

        loop = asyncio.get_running_loop()
        try:
            await loop.getaddrinfo(clean_domain, None)
            return True
        except socket.gaierror:
            return False
        except Exception:
            return False

    @retry(
        retry=retry_if_exception_type(TemporaryError),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=8),
    )
    async def check_http_status(
        self,
        session: aiohttp.ClientSession,
        url: str,
        *,
        proxy: str | None,
    ) -> dict:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        try:
            async with session.get(
                url,
                timeout=self.request_timeout_sec,
                allow_redirects=True,
                proxy=proxy,
                headers=headers,
            ) as response:
                status_code = response.status
                final_url = str(response.url)

            if status_code < 400 or status_code in (400, 401, 403, 405, 412, 429, 999):
                return {"status": "live", "code": status_code, "final_url": final_url}
            if status_code in (404, 410):
                raise DeterministicError(f"HTTP {status_code}")
            if status_code == 502:
                return {"status": "dead", "code": status_code, "final_url": final_url}
            if status_code >= 500:
                return {"status": "unknown", "code": status_code, "final_url": final_url}
            return {"status": "unknown", "code": status_code, "final_url": final_url}
        except (asyncio.TimeoutError, aiohttp.ClientError) as exc:
            raise TemporaryError(str(exc)) from exc

    async def validate_link(self, session: aiohttp.ClientSession, link: ExtractedLink) -> ValidationEvidence:
        try:
            parsed = urlparse(link.url)
            domain = parsed.netloc or parsed.path.split("/", maxsplit=1)[0]
            if not domain:
                raise ValueError("empty domain")
        except ValueError:
            return ValidationEvidence(
                url=link.url,
                domain=link.domain,
                source_field=link.source_field,
                result="dead",
                reason="Malformed URL Format",
                dns_resolved=False,
                position=link.position,
            )

        dns_hint = await self.verify_dns_hint(domain)
        attempts: list[tuple[str | None, bool]] = []
        if self.allow_direct:
            attempts.append((None, False))
        if self.allow_proxy_fallback:
            attempts.append((self.proxy_url, True))

        for proxy, used_proxy in attempts:
            try:
                async with self.semaphore:
                    result = await self.check_http_status(session, link.url, proxy=proxy)
                return ValidationEvidence(
                    url=link.url,
                    domain=link.domain,
                    source_field=link.source_field,
                    result=result["status"],
                    reason=f"Code {result['code']}{' (proxy)' if used_proxy else ' (direct)'}",
                    status_code=result["code"],
                    dns_resolved=dns_hint,
                    final_url=result.get("final_url"),
                    final_domain=(urlparse(result.get("final_url", "")).netloc.lower().rstrip(".") if result.get("final_url") else ""),
                    used_proxy=used_proxy,
                    position=link.position,
                )
            except DeterministicError as exc:
                return ValidationEvidence(
                    url=link.url,
                    domain=link.domain,
                    source_field=link.source_field,
                    result="dead",
                    reason=str(exc),
                    dns_resolved=dns_hint,
                    used_proxy=used_proxy,
                    position=link.position,
                )
            except Exception:
                continue

        return ValidationEvidence(
            url=link.url,
            domain=link.domain,
            source_field=link.source_field,
            result="dead" if not dns_hint else "unknown",
            reason="DNS Unresolved" if not dns_hint else "Connection Failed",
            dns_resolved=dns_hint,
            position=link.position,
        )

    async def process_row(self, session: aiohttp.ClientSession, row: dict, source_fields: tuple[str, ...]) -> dict:
        extracted_links = extract_links_from_fields(row, source_fields)
        tasks = [asyncio.create_task(self.validate_link(session, link)) for link in extracted_links]
        validations = await asyncio.gather(*tasks) if tasks else []

        output_row = dict(row)
        output_row["extracted_links"] = [link.to_dict() for link in extracted_links]
        output_row["validated_links"] = [evidence.to_dict() for evidence in validations]
        output_row["verified_links"] = [
            {
                "url": evidence.url,
                "domain": evidence.domain,
                "final_domain": evidence.final_domain,
                "result": evidence.result,
                "reason": evidence.reason,
            }
            for evidence in validations
        ]
        return output_row


async def validate_rows_async(
    rows: list[dict],
    *,
    concurrency_limit: int,
    proxy_url: str,
    request_timeout_sec: float,
    batch_size: int,
    allow_direct: bool,
    allow_proxy_fallback: bool,
    source_fields: tuple[str, ...],
) -> list[dict]:
    validator = LinkValidator(
        concurrency_limit=concurrency_limit,
        proxy_url=proxy_url,
        request_timeout_sec=request_timeout_sec,
        allow_direct=allow_direct,
        allow_proxy_fallback=allow_proxy_fallback,
    )

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        results: list[dict] = []
        total = len(rows)
        for start in range(0, total, batch_size):
            batch = rows[start : start + batch_size]
            tasks = [asyncio.create_task(validator.process_row(session, row, source_fields)) for row in batch]
            for task in asyncio.as_completed(tasks):
                results.append(await task)
        results.sort(key=lambda row: (row.get("prompt_id", ""), row.get("model", "")))
        return results


def validate_rows(
    rows: list[dict],
    *,
    concurrency_limit: int,
    proxy_url: str,
    request_timeout_sec: float,
    batch_size: int,
    allow_direct: bool,
    allow_proxy_fallback: bool,
    source_fields: tuple[str, ...],
) -> list[dict]:
    if not rows:
        return []
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(
        validate_rows_async(
            rows,
            concurrency_limit=concurrency_limit,
            proxy_url=proxy_url,
            request_timeout_sec=request_timeout_sec,
            batch_size=batch_size,
            allow_direct=allow_direct,
            allow_proxy_fallback=allow_proxy_fallback,
            source_fields=source_fields,
        )
    )
