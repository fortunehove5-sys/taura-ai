"""Very small, dependency-free language hinting for Shona / Ndebele / English.

This is deliberately simple: it counts hits against short marker-word lists
and falls back to config.DEFAULT_LANGUAGE when the signal is weak or absent
(e.g. a bare price figure, or a USSD numeric selection). It exists so the demo
and tests can exercise multilingual responses without a heavyweight language-ID
model. A production build would use a proper langid model or explicit user
language selection captured at session start.
"""
from __future__ import annotations

import re

from .config import DEFAULT_LANGUAGE

_WORD_RE = re.compile(r"[a-zA-Z\u00c0-\u017f']+")

_MARKERS = {
    "sn": [
        "mhoro", "ndiri", "muri", "chii", "sei", "kuti", "hongu", "kwete",
        "mutengo", "mvura", "mari", "ndinoda", "ndinotenda", "makadii",
    ],
    "nd": [
        "sawubona", "ngiyabonga", "yebo", "hatshi", "kanjani", "ini",
        "inani", "izulu", "imali", "ngicela", "salibonani", "unjani",
    ],
    "en": [
        "hello", "hi", "price", "weather", "rain", "loan", "savings",
        "please", "thank", "you", "how", "much",
    ],
}


def detect(text: str) -> str:
    words = set(w.lower() for w in _WORD_RE.findall(text))
    if not words:
        return DEFAULT_LANGUAGE

    scores = {lang: len(words & set(markers)) for lang, markers in _MARKERS.items()}
    best_lang = max(scores, key=scores.get)
    if scores[best_lang] == 0:
        return DEFAULT_LANGUAGE
    return best_lang
