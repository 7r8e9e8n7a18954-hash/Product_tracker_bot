import unittest

from app.adapters.amazon_in import AmazonIndiaAdapter
from app.adapters.flipkart import FlipkartAdapter
from app.adapters.meesho import MeeshoAdapter


SAMPLE_HTML = '''<!doctype html><html><head><title>Sample</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"Demo Headphones",
 "offers":{"@type":"Offer","price":"1299.00","priceCurrency":"INR","availability":"https://schema.org/InStock"}}
</script></head><body></body></html>'''


class AdapterTests(unittest.TestCase):
    def test_supported_domains(self):
        self.assertTrue(AmazonIndiaAdapter().supports("https://www.amazon.in/dp/example"))
        self.assertTrue(FlipkartAdapter().supports("https://www.flipkart.com/item/p/abc"))
        self.assertTrue(MeeshoAdapter().supports("https://www.meesho.com/item/p/abc"))
        self.assertFalse(FlipkartAdapter().supports("https://flipkart.com.attacker.example/item"))
        self.assertFalse(AmazonIndiaAdapter().supports("http://www.amazon.in/dp/example"))

    def test_parses_jsonld_product(self):
        adapter = FlipkartAdapter()
        result = adapter.parse_product(SAMPLE_HTML, "https://www.flipkart.com/item")
        self.assertEqual(result.title, "Demo Headphones")
        self.assertEqual(result.price, 1299.0)
        self.assertEqual(result.currency, "INR")
        self.assertEqual(result.shop, "Flipkart India")

    def test_missing_price_is_not_guessed(self):
        adapter = MeeshoAdapter()
        result = adapter.parse_product("<html><head><title>Only title</title></head></html>", "https://www.meesho.com/item")
        self.assertIsNone(result.price)
        self.assertIsNone(result.currency)


if __name__ == "__main__":
    unittest.main()
