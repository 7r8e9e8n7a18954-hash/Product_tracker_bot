import unittest
from app.security import validate_product_url

class URLValidationTests(unittest.TestCase):
    def test_accepts_https_domain(self):
        ok, value = validate_product_url("https://example.com/product/123")
        self.assertTrue(ok)
        self.assertEqual(value, "https://example.com/product/123")

    def test_rejects_javascript_scheme(self):
        ok, _ = validate_product_url("javascript:alert(1)")
        self.assertFalse(ok)

    def test_rejects_localhost(self):
        ok, _ = validate_product_url("http://localhost/admin")
        self.assertFalse(ok)

    def test_rejects_private_ip(self):
        ok, _ = validate_product_url("http://127.0.0.1/test")
        self.assertFalse(ok)

    def test_rejects_embedded_credentials(self):
        ok, _ = validate_product_url("https://user:pass@example.com/item")
        self.assertFalse(ok)

if __name__ == "__main__":
    unittest.main()
