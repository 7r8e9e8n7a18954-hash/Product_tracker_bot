"""Product adapters for supported shopping domains."""

from app.adapters.amazon_in import AmazonIndiaAdapter
from app.adapters.flipkart import FlipkartAdapter
from app.adapters.meesho import MeeshoAdapter

__all__ = ["AmazonIndiaAdapter", "FlipkartAdapter", "MeeshoAdapter"]
