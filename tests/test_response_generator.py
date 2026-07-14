import pytest

from taura.entity_extractor import ExtractedEntities
from taura.rag_retriever import RagRetriever
from taura.response_generator import LLMResponseGenerator, TemplateResponseGenerator


@pytest.fixture
def retriever():
    return RagRetriever()


def test_phrase_price_shona(retriever):
    record = retriever.find_price(ExtractedEntities(commodity="maize", location="Mutare"))
    gen = TemplateResponseGenerator()
    text = gen.phrase_price(record, "sn")
    assert "14.50" in text
    assert "Mutare" in text


def test_phrase_price_english(retriever):
    record = retriever.find_price(ExtractedEntities(commodity="maize", location="Mutare"))
    gen = TemplateResponseGenerator()
    text = gen.phrase_price(record, "en")
    assert "Maize" in text
    assert "$14.50" in text


def test_phrase_climate_ndebele(retriever):
    record = retriever.find_climate_alert(ExtractedEntities(commodity=None, location="Chipinge"))
    gen = TemplateResponseGenerator()
    text = gen.phrase_climate(record, "nd")
    assert text == record.data["message_nd"]


def test_no_data_found_has_all_languages():
    gen = TemplateResponseGenerator()
    for lang in ("en", "sn", "nd"):
        assert gen.no_data_found(lang)


def test_llm_generator_raises_until_configured(retriever):
    record = retriever.find_price(ExtractedEntities(commodity="maize", location="Mutare"))
    gen = LLMResponseGenerator()
    with pytest.raises(NotImplementedError):
        gen.phrase_price(record, "en")
