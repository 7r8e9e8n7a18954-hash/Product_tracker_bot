from urllib.parse import urlparse

from app.adapters.contracts import ProductSnapshot, ShopAdapter


class AdapterRegistry:
    def __init__(self):
        self.adapters: list[ShopAdapter] = []

    def register(self, adapter: ShopAdapter) -> None:
        self.adapters.append(adapter)

    def find(self, url: str) -> ShopAdapter | None:
        return next((adapter for adapter in self.adapters if adapter.supports(url)), None)

    async def inspect(self, url: str) -> ProductSnapshot:
        adapter = self.find(url)
        if not adapter:
            host = urlparse(url).hostname or "unknown"
            return ProductSnapshot(
                shop=host,
                title="Unverified product link",
                price=None,
                currency=None,
                product_url=url,
                note="No adapter is configured for this website. Supported shops: Amazon India, Flipkart India, and Meesho India.",
            )
        return await adapter.fetch(url)

    def search_links(self, query: str) -> list[tuple[str, str]]:
        """Build direct shop-search links; does not scrape search engines or claim matches."""
        from urllib.parse import quote_plus
        q = quote_plus(query.strip())
        return [
            ("Amazon India", f"https://www.amazon.in/s?k={q}"),
            ("Flipkart", f"https://www.flipkart.com/search?q={q}"),
            ("Meesho", f"https://www.meesho.com/search?q={q}"),
        ]


registry = AdapterRegistry()

# Register only known, explicit domains. These adapters read public structured
# metadata and do not bypass login walls, CAPTCHAs, or access restrictions.
from app.adapters import AmazonIndiaAdapter, FlipkartAdapter, MeeshoAdapter  # noqa: E402

registry.register(AmazonIndiaAdapter())
registry.register(FlipkartAdapter())
registry.register(MeeshoAdapter())
