import os
import tempfile
import unittest
from app.database import Database
from app.shops import registry


class FeatureTests(unittest.TestCase):
    def test_search_links_are_created_for_supported_shops(self):
        links = registry.search_links("wireless headphones")
        self.assertEqual(len(links), 3)
        self.assertTrue(all(url.startswith("https://") for _, url in links))
        self.assertIn("wireless+headphones", links[0][1])

    def test_price_history_and_previous_price(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(os.path.join(folder, "test.db"))
            added, product_id = db.add_product(123, "https://www.flipkart.com/item", 10)
            self.assertTrue(added)
            self.assertIsNone(db.save_price(product_id, 1200.0, "INR", "Headphones", "Flipkart India"))
            self.assertEqual(db.save_price(product_id, 1000.0, "INR", "Headphones", "Flipkart India"), 1200.0)
            history = db.get_price_history(123, product_id, 10)
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]["price"], 1000.0)
            self.assertEqual(db.get_price_history(999, product_id), [])


if __name__ == "__main__":
    unittest.main()
