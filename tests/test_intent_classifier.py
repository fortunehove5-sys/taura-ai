from taura.intent_classifier import Intent, classify


def test_greeting_shona():
    result = classify("Mhoro, makadii")
    assert result.intent == Intent.GREETING


def test_greeting_ndebele():
    result = classify("Sawubona")
    assert result.intent == Intent.GREETING


def test_price_query_english():
    result = classify("what is the price of maize")
    assert result.intent == Intent.PRICE_QUERY


def test_price_query_shona():
    result = classify("mutengo wechibage muMutare")
    assert result.intent == Intent.PRICE_QUERY


def test_climate_query_ndebele():
    result = classify("isikhukhula eChipinge")
    assert result.intent == Intent.CLIMATE_QUERY


def test_climate_query_english():
    result = classify("is it going to rain this week")
    assert result.intent == Intent.CLIMATE_QUERY


def test_financial_query_shona():
    result = classify("ndinoda chikwereti chembeu")
    assert result.intent == Intent.FINANCIAL_QUERY


def test_human_handoff():
    result = classify("I want to speak to a human agent")
    assert result.intent == Intent.HUMAN_HANDOFF


def test_consent_yes_variants():
    for phrase in ["hongu", "yebo", "yes"]:
        assert classify(phrase).intent == Intent.CONSENT_YES


def test_consent_no_variants():
    for phrase in ["kwete", "hatshi", "no"]:
        assert classify(phrase).intent == Intent.CONSENT_NO


def test_unknown_for_gibberish():
    result = classify("zxqwjk flimflam")
    assert result.intent == Intent.UNKNOWN


def test_empty_string_is_unknown():
    result = classify("")
    assert result.intent == Intent.UNKNOWN
