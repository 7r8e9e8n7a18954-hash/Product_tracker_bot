"""Shared, conservative HTML/JSON-LD product adapter.

Only reads ordinary public product pages. It does not bypass CAPTCHAs,
logins, anti-bot protections, or access restrictions. Use only where the
shop's terms and applicable law permit this access.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from app.security import is_public_ip
from app.adapters.contracts import ProductSnapshot, ShopAdapter


@dataclass(frozen=True)
class AdapterConfig:
    shop_name: str
    domains: tuple[str, ...]


class StructuredDataAdapter(ShopAdapter):
    """Extract product fields from JSON-LD and Open Graph metadata."""

    config: AdapterConfig
    timeout_seconds = 12
    max_html_bytes = 2_000_000
    max_redirects = 3

    @property
    def shop_name(self) -> str:
        return self.config.shop_name

    def supports(self, url: str) -> bool:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        return (
            parsed.scheme == "https"
            and not parsed.username
            and not parsed.password
            and any(host == domain or host.endswith("." + domain) for domain in self.config.domains)
        )

    def _host_is_public(self, url: str) -> bool:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host or parsed.scheme != "https" or parsed.port not in (None, 443):
            return False
        return is_public_ip(host)

    async def _read_html(self, url: str) -> tuple[str, str]:
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds, connect=5)
        headers = {
            "User-Agent": "ProductsDetailTrackBot/1.0 (product metadata; contact: bot administrator)",
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
        }
        current_url = url
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            for redirect_count in range(self.max_redirects + 1):
                # Only fetch the exact shop domain this adapter is responsible for.
                if not self.supports(current_url) or not await asyncio.to_thread(self._host_is_public, current_url):
                    raise ValueError("URL host is not an allowed public shop host")
                async with session.get(current_url, allow_redirects=False) as response:
                    if response.status in (301, 302, 303, 307, 308):
                        if redirect_count >= self.max_redirects:
                            raise ValueError("Too many redirects")
                        location = response.headers.get("Location")
                        if not location:
                            raise ValueError("Redirect did not include a destination")
                        current_url = urljoin(current_url, location)
                        continue
                    if response.status in (401, 403, 429, 503):
                        raise ValueError(f"Shop declined automated access (HTTP {response.status})")
                    response.raise_for_status()
                    content_type = response.headers.get("Content-Type", "").lower()
                    if "html" not in content_type:
                        raise ValueError("The product link did not return an HTML page")
                    raw = await response.content.read(self.max_html_bytes + 1)
                    if len(raw) > self.max_html_bytes:
                        raise ValueError("Product page is too large to inspect")
                    encoding = response.charset or "utf-8"
                    return raw.decode(encoding, errors="replace"), str(response.url)
        raise ValueError("Could not load product page")

    @staticmethod
    def _iter_json_objects(value: Any):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from StructuredDataAdapter._iter_json_objects(child)
        elif isinstance(value, list):
            for child in value:
                yield from StructuredDataAdapter._iter_json_objects(child)

    @staticmethod
    def _is_product(obj: dict[str, Any]) -> bool:
        kind = obj.get("@type", [])
        if isinstance(kind, str):
            kind = [kind]
        return any(str(item).lower() == "product" for item in kind)

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if isinstance(value, dict):
            value = value.get("name") or value.get("value")
        if not isinstance(value, (str, int, float)):
            return None
        cleaned = re.sub(r"\s+", " ", str(value)).strip()
        return cleaned[:300] if cleaned else None

    @staticmethod
    def _price_and_currency(offers: Any) -> tuple[float | None, str | None, str | None]:
        if isinstance(offers, list):
            for offer in offers:
                result = StructuredDataAdapter._price_and_currency(offer)
                if result[0] is not None:
                    return result
            return None, None, None
        if not isinstance(offers, dict):
            return None, None, None
        raw_price = offers.get("price")
        if raw_price is None:
            raw_price = offers.get("lowPrice")
        currency = offers.get("priceCurrency")
        availability = offers.get("availability")
        if isinstance(availability, str):
            availability = availability.rsplit("/", 1)[-1]
        try:
            price = float(Decimal(str(raw_price).replace(",", "").strip()))
            if price < 0:
                return None, None, None
        except (InvalidOperation, ValueError, TypeError):
            return None, str(currency) if currency else None, str(availability) if availability else None
        return price, str(currency) if currency else None, str(availability) if availability else None

    def parse_product(self, html: str, final_url: str) -> ProductSnapshot:
        soup = BeautifulSoup(html, "html.parser")
        title = None
        price = None
        currency = None
        availability = None

        # Prefer schema.org Product JSON-LD because it has structured fields.
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = script.string or script.get_text()
            if not raw or len(raw) > 500_000:
                continue
            try:
                payload = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            for obj in self._iter_json_objects(payload):
                if not self._is_product(obj):
                    continue
                title = self._clean_text(obj.get("name")) or title
                found_price, found_currency, found_availability = self._price_and_currency(obj.get("offers"))
                if price is None and found_price is not None:
                    price, currency, availability = found_price, found_currency, found_availability
                if title and price is not None:
                    break
            if title and price is not None:
                break

        def meta(*keys: str) -> str | None:
            for key in keys:
                tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
                if tag and tag.get("content"):
                    return self._clean_text(tag["content"])
            return None

        title = title or meta("og:title", "twitter:title")
        if price is None:
            raw_price = meta("product:price:amount", "og:price:amount")
            try:
                price = float(Decimal(raw_price)) if raw_price else None
                if price is not None and price < 0:
                    price = None
            except (InvalidOperation, ValueError, TypeError):
                price = None
            currency = meta("product:price:currency", "og:price:currency")
        title = title or self._clean_text(soup.title.get_text(" ", strip=True) if soup.title else None)

        if not title and price is None:
            note = "Page loaded, but no verifiable product title or price metadata was found."
        elif price is None:
            note = "Product title found; no verifiable price metadata was found."
        else:
            note = "Price read from the page's structured metadata; availability may change."
        return ProductSnapshot(
            shop=self.shop_name,
            title=title or "Product details unavailable",
            price=price,
            currency=currency,
            product_url=final_url,
            note=note,
        )

    async def fetch(self, url: str) -> ProductSnapshot:
        if not self.supports(url):
            raise ValueError("This adapter does not support that URL")
        try:
            html, final_url = await self._read_html(url)
            return self.parse_product(html, final_url)
        except (aiohttp.ClientError, asyncio.TimeoutError, UnicodeError, ValueError) as exc:
            return ProductSnapshot(
                shop=self.shop_name,
                title="Product details unavailable",
                price=None,
                currency=None,
                product_url=url,
                note=f"Could not verify product data: {str(exc)[:180]}. No price was guessed.",
            )
