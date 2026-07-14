from taura.entity_extractor import extract


def test_extracts_commodity_alias_shona():
    result = extract("mutengo wechibage muMutare")
    assert result.commodity == "maize"


def test_extracts_commodity_alias_ndebele():
    result = extract("inani likaumbila eBulawayo")
    assert result.commodity == "maize"


def test_extracts_commodity_english():
    result = extract("what is the price of groundnuts")
    assert result.commodity == "groundnuts"


def test_extracts_location():
    result = extract("kuzonaya here muGokwe")
    assert result.location == "Gokwe"


def test_no_entities_found():
    result = extract("hello there")
    assert result.commodity is None
    assert result.location is None


def test_extracts_both_commodity_and_location():
    result = extract("sorghum price in Masvingo please")
    assert result.commodity == "sorghum"
    assert result.location == "Masvingo"
