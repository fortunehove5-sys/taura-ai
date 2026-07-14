"""Structured audit logging for every Taura session turn.

Writes one JSON object per line to logs/audit.log. This is the mechanism
referenced in the written proposal (Section 2.2 / 4.1): every turn records the
detected intent, the retrieved source record id (never the raw personal data
of other users), and the outcome, to support monitoring and Data Protection
Act [Chapter 12:07] auditability.

Raw audio is deliberately NOT logged here; only the transcribed text and the
structured outcome are recorded, consistent with the data-minimisation
approach described in the proposal.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Optional

from .config import AUDIT_LOG_PATH


@dataclass
class AuditEntry:
    session_id: str
    channel: str
    language: str
    consent_status: str
    intent: str
    retrieved_source_id: Optional[str]
    outcome: str  # e.g. "answered", "escalated", "declined_no_consent", "unknown_intent"
    timestamp: float


def write_entry(entry: AuditEntry) -> None:
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")


def new_entry(
    session_id: str,
    channel: str,
    language: str,
    consent_status: str,
    intent: str,
    retrieved_source_id: Optional[str],
    outcome: str,
) -> AuditEntry:
    entry = AuditEntry(
        session_id=session_id,
        channel=channel,
        language=language,
        consent_status=consent_status,
        intent=intent,
        retrieved_source_id=retrieved_source_id,
        outcome=outcome,
        timestamp=time.time(),
    )
    write_entry(entry)
    return entry


def read_all_entries() -> list[dict]:
    """Utility for the admin console / tests: read back all logged entries."""
    if not AUDIT_LOG_PATH.exists():
        return []
    entries = []
    with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries
