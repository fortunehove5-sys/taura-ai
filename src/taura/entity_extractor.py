"""Lightweight entity extraction: commodity and location.

Matches against the alias lists already present in the sample data files, plus
a small static gazetteer of Zimbabwean districts/towns. This keeps the demo
dependency-free (no spaCy / heavy NLP models) while still being genuinely
data-driven: adding a new commodity alias to data/market_prices.json makes it
extractable here without a code change.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .config import DATA_DIR

_WORD_RE = re.compile(r"[a-zA-Z\u00c0-\u017f']+")

# Small static gazetteer. Extend as the pilot expands to new districts.
KNOWN_LOCATIONS = [
    "Mutare", "Gokwe", "Masvingo", "Harare", "Bulawayo", "Chipinge",
    "Chiredzi", "Binga", "Beitbridge", "Kwekwe", "Gweru", "Mutoko",
    "Chirumhanzu", "Tsholotsho", "Rusape", "Marondera",
]


def _load_commodity_aliases() -> dict[str, str]:
    """Build a lowercase alias -> canonical commodity name map from the price data."""
    path = Path(DATA_DIR) / "market_prices.json"
    aliases: dict[str, str] = {}
    if not path.exists():
        return aliases
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    for record in payload.get("records", []):
        commodity = record["commodity"]
        aliases[commodity.lower()] = commodity
        for alias in record.get("commodity_aliases", []):
            aliases[alias.lower()] = commodity
    return aliases


_COMMODITY_ALIASES = _load_commodity_aliases()


@dataclass
class ExtractedEntities:
    commodity: str | None
    location: str | None


def extract(text: str) -> ExtractedEntities:
    words = set(w.lower() for w in _WORD_RE.findall(text))

    commodity = None
    for alias, canonical in _COMMODITY_ALIASES.items():
        if alias in words or alias in text.lower():
            commodity = canonical
            break

    location = None
    lowered = text.lower()
    for loc in KNOWN_LOCATIONS:
        if loc.lower() in lowered:
            location = loc
            break

    return ExtractedEntities(commodity=commodity, location=location)
