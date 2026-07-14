"""Session-level consent tracking.

This is an in-memory reference implementation. In production, consent state
belongs in the session store (a real database), keyed by phone number / WhatsApp
ID / USSD session ID, and must persist across sessions for the same user.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ConsentStatus(str, Enum):
    UNKNOWN = "unknown"
    GRANTED = "granted"
    DECLINED = "declined"


@dataclass
class ConsentStore:
    """Tracks consent per session_id. Swap for a DB-backed store in production."""

    _state: dict = field(default_factory=dict)

    def get(self, session_id: str) -> ConsentStatus:
        return self._state.get(session_id, ConsentStatus.UNKNOWN)

    def grant(self, session_id: str) -> None:
        self._state[session_id] = ConsentStatus.GRANTED

    def decline(self, session_id: str) -> None:
        self._state[session_id] = ConsentStatus.DECLINED

    def reset(self, session_id: str) -> None:
        self._state.pop(session_id, None)

    def is_resolved(self, session_id: str) -> bool:
        return self.get(session_id) != ConsentStatus.UNKNOWN
