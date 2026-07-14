"""Deterministic, multilingual (Shona / Ndebele / English) intent classifier.

WHY RULE-BASED HERE, NOT A NEURAL MODEL:
This module is a fast, fully-offline, testable first pass that is enough to
demonstrate and validate the product's routing logic without requiring GPU
inference or network access to run the test suite / CI. In the architecture
described in the written proposal, this component sits *after* ASR and can be
upgraded to a small fine-tuned multilingual transformer classifier without any
change to the orchestrator or downstream RAG/response-generation code, because
it only needs to expose `classify(text) -> Intent`.

The keyword lists below are intentionally small and illustrative. A production
version would be trained/validated on real, consented user utterances collected
during the pilot (see docs/DATASET_STATEMENT.md).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    GREETING = "greeting"
    PRICE_QUERY = "price_query"
    CLIMATE_QUERY = "climate_query"
    FINANCIAL_QUERY = "financial_query"
    HUMAN_HANDOFF = "human_handoff"
    CONSENT_YES = "consent_yes"
    CONSENT_NO = "consent_no"
    UNKNOWN = "unknown"


# Keyword -> intent votes. Kept lowercase; matching is done on normalised text.
_KEYWORDS: dict[Intent, list[str]] = {
    Intent.GREETING: [
        "mhoro", "hesi", "makadii", "salibonani", "sawubona", "unjani",
        "hello", "hi", "hie", "good morning", "good afternoon",
    ],
    Intent.PRICE_QUERY: [
        "mutengo", "mitengo", "muripo", "inani", "amanani", "amanani wentengo",
        "price", "prices", "cost", "how much",
    ],
    Intent.CLIMATE_QUERY: [
        "mvura", "kunaya", "kuzonaya", "kunonaya", "mamiriro ekunze", "mafashame",
        "chirimo", "izulu", "isimo sezulu", "isikhukhula", "isomiso",
        "weather", "rain", "rains", "raining", "flood", "flooding", "drought", "forecast",
    ],
    Intent.FINANCIAL_QUERY: [
        "mari", "chikwereti", "kuchengetedza", "chibhengi", "inishuwarenzi",
        "imali", "isikwelede", "ukonga", "ibhange", "inshurensi",
        "loan", "savings", "save", "credit", "insurance", "bank", "ecocash",
    ],
    Intent.HUMAN_HANDOFF: [
        "munhu", "tibatane nemunhu", "ndinoda munhu",
        "umuntu", "ngicela umuntu",
        "agent", "human", "operator", "speak to someone",
    ],
    Intent.CONSENT_YES: ["hongu", "ehe", "yebo", "yes", "y"],
    Intent.CONSENT_NO: ["kwete", "hatshi", "no", "n"],
}

_WORD_RE = re.compile(r"[a-zA-Z\u00c0-\u017f']+")


def _normalise(text: str) -> str:
    return " ".join(_WORD_RE.findall(text.lower()))


@dataclass
class ClassificationResult:
    intent: Intent
    confidence: float  # naive vote-share confidence, 0..1
    matched_keywords: list[str]


def classify(text: str) -> ClassificationResult:
    """Classify a single user utterance into one Intent.

    Consent replies (yes/no) are only meaningful mid-flow; the orchestrator is
    responsible for interpreting CONSENT_YES/NO only when a consent prompt is
    pending, and otherwise treating a bare "yes"/"hongu" as UNKNOWN.
    """
    normalised = _normalise(text)
    if not normalised:
        return ClassificationResult(Intent.UNKNOWN, 0.0, [])

    scores: dict[Intent, list[str]] = {intent: [] for intent in _KEYWORDS}
    for intent, keywords in _KEYWORDS.items():
        for kw in keywords:
            compact = kw.replace(" ", "")
            if len(compact) <= 3:
                # Short keywords (e.g. "hi", "no", "y") are prone to false
                # positives as substrings of unrelated words (e.g. "hi" inside
                # the Shona word "chibage"), so they must land on a real word
                # boundary.
                pattern = r"\b" + re.escape(kw) + r"\b"
                matched = bool(re.search(pattern, normalised))
            else:
                # Longer, more distinctive keywords use substring matching so
                # that agglutinated Shona/Ndebele forms are still recognised
                # (e.g. "munhu" inside "nemunhu" = "ne" + "munhu", a single
                # written token with no internal space).
                matched = kw in normalised
            if matched:
                scores[intent].append(kw)

    non_empty = {i: kws for i, kws in scores.items() if kws}
    if not non_empty:
        return ClassificationResult(Intent.UNKNOWN, 0.0, [])

    best_intent = max(non_empty, key=lambda i: len(non_empty[i]))
    matched = non_empty[best_intent]
    total_matches = sum(len(kws) for kws in non_empty.values())
    confidence = len(matched) / total_matches if total_matches else 0.0
    return ClassificationResult(best_intent, round(confidence, 2), matched)
