from taura.entity_extractor import ExtractedEntities
from taura.rag_retriever import RagRetriever


def test_find_price_by_commodity_and_location():
    retriever = RagRetriever()
    record = retriever.find_price(ExtractedEntities(commodity="maize", location="Mutare"))
    assert record is not None
    assert record.data["commodity"] == "maize"
    assert record.data["location"] == "Mutare"


def test_find_price_missing_returns_none():
    retriever = RagRetriever()
    record = retriever.find_price(ExtractedEntities(commodity="coffee", location="Mutare"))
    assert record is None


def test_find_climate_alert_by_location():
    retriever = RagRetriever()
    record = retriever.find_climate_alert(ExtractedEntities(commodity=None, location="Chipinge"))
    assert record is not None
    assert record.data["alert_type"] == "flood_warning"


def test_find_climate_alert_no_location_returns_none():
    retriever = RagRetriever()
    record = retriever.find_climate_alert(ExtractedEntities(commodity=None, location=None))
    assert record is None


def test_find_financial_products_returns_all():
    retriever = RagRetriever()
    records = retriever.find_financial_products()
    assert len(records) == 3


def test_find_financial_products_by_topic():
    retriever = RagRetriever()
    records = retriever.find_financial_products(topic_hint="savings")
    assert len(records) == 1
    assert records[0].data["topic"] == "savings"


def test_find_knowledge_greeting():
    retriever = RagRetriever()
    record = retriever.find_knowledge("greeting")
    assert record is not None
    assert "message_en" in record.data
