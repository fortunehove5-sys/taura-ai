"""Turns a retrieved record into a short, spoken-style response in the user's language.

Two backends implement the same `ResponseGenerator` interface:

- `TemplateResponseGenerator` (default): deterministic, fully offline, no
  external calls. This is what the automated tests and the bundled demo use,
  and it is sufficient to validate the product logic end-to-end.
- `LLMResponseGenerator`: a thin adapter showing where a real instruction-tuned
  language model (e.g. a quantized Llama-3-8B, or a hosted API) plugs in. It is
  NOT wired to any network call by default -- `generate()` raises
  NotImplementedError until a provider is configured -- so the repository has
  no hidden external dependency or cost at demo time.

CRITICAL DESIGN RULE (see written proposal, Section 2.3): whichever backend is
used, it is only ever given a *retrieved* record to phrase. It is never asked
to answer a price/weather/financial question from unguided generation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .rag_retriever import RetrievedRecord


class ResponseGenerator(ABC):
    @abstractmethod
    def phrase_price(self, record: RetrievedRecord, language: str) -> str: ...

    @abstractmethod
    def phrase_climate(self, record: RetrievedRecord, language: str) -> str: ...

    @abstractmethod
    def phrase_financial(self, records: list[RetrievedRecord], language: str) -> str: ...

    @abstractmethod
    def phrase_knowledge(self, record: RetrievedRecord, language: str) -> str: ...

    @abstractmethod
    def no_data_found(self, language: str) -> str: ...


_TREND_WORD = {
    "en": {"up": "rising", "down": "falling", "stable": "steady"},
    "sn": {"up": "achikwira", "down": "achidzika", "stable": "akagara"},
    "nd": {"up": "ekhuphuka", "down": "ehla", "stable": "emile"},
}

# Canonical (English) commodity name -> display name per language. Falls back
# to the canonical English name if a translation is not yet registered here,
# so adding a new commodity to data/market_prices.json never breaks response
# generation -- it just won't be translated until this map is extended.
_COMMODITY_NAME = {
    "maize": {"sn": "chibage", "nd": "umbila", "en": "maize"},
    "groundnuts": {"sn": "nzungu", "nd": "indlubu", "en": "groundnuts"},
    "sorghum": {"sn": "mapfunde", "nd": "amabele", "en": "sorghum"},
    "soybeans": {"sn": "soya", "nd": "i-soya", "en": "soybeans"},
}


def _commodity_display_name(commodity: str, language: str) -> str:
    entry = _COMMODITY_NAME.get(commodity, {})
    return entry.get(language, commodity)


_NO_DATA = {
    "en": "I don't have verified information for that yet. Let me connect you to a support agent.",
    "sn": "Handisati ndave neruzivo rwakasimbiswa pamusoro peizvi. Regai ndikubatanidzei nemubatsiri.",
    "nd": "Kangilalo ulwazi oluqinisekisiweyo ngalokhu okwamanje. Ake ngikuxhumanise lomsizi.",
}


class TemplateResponseGenerator(ResponseGenerator):
    """Deterministic phrase-templates per language. No network access required."""

    def phrase_price(self, record: RetrievedRecord, language: str) -> str:
        d = record.data
        trend = _TREND_WORD.get(language, _TREND_WORD["en"]).get(d.get("price_trend", "stable"))
        commodity_name = _commodity_display_name(d["commodity"], language)
        if language == "sn":
            return (
                f"Mutengo we{commodity_name} muno{d['location']} ndeve $"
                f"{d['price_usd']:.2f} {d['unit']}, uri {trend} (vhiki {d['week']})."
            )
        if language == "nd":
            return (
                f"Intengo ye{commodity_name} e{d['location']} yi-$"
                f"{d['price_usd']:.2f} {d['unit']}, {trend} (iviki {d['week']})."
            )
        return (
            f"{commodity_name.capitalize()} price in {d['location']} is "
            f"${d['price_usd']:.2f} {d['unit']}, currently {trend} (week {d['week']})."
        )

    def phrase_climate(self, record: RetrievedRecord, language: str) -> str:
        d = record.data
        key = {"sn": "message_sn", "nd": "message_nd"}.get(language, "message_en")
        return d.get(key, d.get("message_en", ""))

    def phrase_financial(self, records: list[RetrievedRecord], language: str) -> str:
        if not records:
            return self.no_data_found(language)
        key = {"sn": "summary_sn", "nd": "summary_nd"}.get(language, "summary_en")
        name_key = {"sn": "name_en", "nd": "name_en"}.get(language, "name_en")  # names kept in EN as product labels
        lines = []
        for r in records[:2]:  # keep spoken responses short
            d = r.data
            lines.append(f"{d.get(name_key, d['name_en'])}: {d.get(key, d['summary_en'])}")
        return "\n".join(lines)

    def phrase_knowledge(self, record: RetrievedRecord, language: str) -> str:
        d = record.data
        key = {"sn": "message_sn", "nd": "message_nd"}.get(language, "message_en")
        return d.get(key, d.get("message_en", ""))

    def no_data_found(self, language: str) -> str:
        return _NO_DATA.get(language, _NO_DATA["en"])


class LLMResponseGenerator(ResponseGenerator):
    """Adapter stub for a real language-model backend.

    To activate: implement `_call_model()` against your chosen provider (a
    local quantized model via e.g. llama-cpp-python, or a hosted API) and set
    TAURA_RESPONSE_BACKEND=llm. Until then this class intentionally raises
    NotImplementedError so the repository never makes a silent network call.
    """

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider

    def _call_model(self, system_prompt: str, grounding_record: dict, language: str) -> str:
        raise NotImplementedError(
            "LLMResponseGenerator is a wiring stub. Implement _call_model() "
            "against your chosen model/provider before setting "
            "TAURA_RESPONSE_BACKEND=llm."
        )

    def phrase_price(self, record: RetrievedRecord, language: str) -> str:
        return self._call_model("Phrase this verified price record naturally.", record.data, language)

    def phrase_climate(self, record: RetrievedRecord, language: str) -> str:
        return self._call_model("Phrase this verified climate alert naturally.", record.data, language)

    def phrase_financial(self, records: list[RetrievedRecord], language: str) -> str:
        return self._call_model(
            "Phrase these verified financial product summaries naturally.",
            {"records": [r.data for r in records]},
            language,
        )

    def phrase_knowledge(self, record: RetrievedRecord, language: str) -> str:
        return self._call_model("Phrase this message naturally.", record.data, language)

    def no_data_found(self, language: str) -> str:
        return _NO_DATA.get(language, _NO_DATA["en"])


def get_response_generator(backend: str = "template") -> ResponseGenerator:
    if backend == "llm":
        return LLMResponseGenerator()
    return TemplateResponseGenerator()
