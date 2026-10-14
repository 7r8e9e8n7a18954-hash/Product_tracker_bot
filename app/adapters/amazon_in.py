from app.adapters.base import AdapterConfig, StructuredDataAdapter


class AmazonIndiaAdapter(StructuredDataAdapter):
    config = AdapterConfig("Amazon India", ("amazon.in",))
