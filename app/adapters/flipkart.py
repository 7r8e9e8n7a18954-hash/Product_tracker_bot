from app.adapters.base import AdapterConfig, StructuredDataAdapter


class FlipkartAdapter(StructuredDataAdapter):
    config = AdapterConfig("Flipkart India", ("flipkart.com",))
