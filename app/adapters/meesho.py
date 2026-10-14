from app.adapters.base import AdapterConfig, StructuredDataAdapter


class MeeshoAdapter(StructuredDataAdapter):
    config = AdapterConfig("Meesho India", ("meesho.com",))
