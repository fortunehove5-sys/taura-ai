"""Retrieval layer that grounds every substantive answer in a verified source record.

This is the component described in Section 2.2 of the written proposal as the
"RAG" step: the response generator is *never* allowed to answer a price,
weather or financial-product question without a retrieved record backing it.
If retrieval finds nothing, the orchestrator must fall back to a "not
available" response or a human handoff rather than letting the language layer
guess.

In production, `load_*` below would point at a live feed / scheduled ingest
from AMA, MSD, Civil Protection and partner MFI/EcoCash APIs instead of the
bundled JSON sample files. The retrieval interface (`find_*`) does not need to
change when that swap happens.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import DATA_DIR
from .entity_extractor import ExtractedEntities


def _load(filename: str) -> list[dict]:
    path = Path(DATA_DIR) / filename
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("records", [])


@dataclass
class RetrievedRecord:
    source_id: str
    data: dict


class RagRetriever:
    """Loads all sample data sources once and exposes intent-scoped lookups."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = data_dir or DATA_DIR
        self.prices = _load("market_prices.json")
        self.alerts = _load("climate_alerts.json")
        self.financial = _load("financial_products.json")
        self.knowledge = _load("knowledge_base.json")

    # -- Price queries ----------------------------------------------------
    def find_price(self, entities: ExtractedEntities) -> Optional[RetrievedRecord]:
        if not entities.commodity:
            # No commodity was identified in the query at all -- returning an
            # arbitrary price record here would violate the grounding rule in
            # Section 2.3 of the written proposal (never answer without a
            # genuinely matched source). Fail closed instead.
            return None
        candidates = [r for r in self.prices if r["commodity"] == entities.commodity]
        if entities.location:
            loc_matches = [r for r in candidates if r["location"] == entities.location]
            if loc_matches:
                candidates = loc_matches
        if not candidates:
            return None
        # Most recent-week record first (sample data uses a single week, but
        # this keeps the retriever correct if multiple weeks are loaded).
        best = sorted(candidates, key=lambda r: r.get("week", ""), reverse=True)[0]
        return RetrievedRecord(source_id=best["id"], data=best)

    # -- Climate queries ----------------------------------------------------
    def find_climate_alert(self, entities: ExtractedEntities) -> Optional[RetrievedRecord]:
        if not entities.location:
            return None
        for record in self.alerts:
            if record["location"] == entities.location:
                return RetrievedRecord(source_id=record["id"], data=record)
        return None

    # -- Financial queries ----------------------------------------------------
    def find_financial_products(self, topic_hint: Optional[str] = None) -> list[RetrievedRecord]:
        records = self.financial
        if topic_hint:
            filtered = [r for r in records if r["topic"] == topic_hint]
            if filtered:
                records = filtered
        return [RetrievedRecord(source_id=r["id"], data=r) for r in records]

    # -- Knowledge base (greeting / handoff / consent copy) -----------------
    def find_knowledge(self, topic: str) -> Optional[RetrievedRecord]:
        for record in self.knowledge:
            if record["topic"] == topic:
                return RetrievedRecord(source_id=record["id"], data=record)
        return None
