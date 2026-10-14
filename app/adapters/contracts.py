from dataclasses import dataclass


@dataclass
class ProductSnapshot:
    shop: str
    title: str
    price: float | None
    currency: str | None
    product_url: str
    note: str = ""


class ShopAdapter:
    """Implement one adapter per shop, respecting that shop's terms and access rules."""
    shop_name = "unknown"

    def supports(self, url: str) -> bool:
        return False

    async def fetch(self, url: str) -> ProductSnapshot:
        raise NotImplementedError
