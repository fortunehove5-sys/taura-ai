"""WhatsApp channel simulator.

Demonstrates how the same Orchestrator serves the WhatsApp channel. A real
integration replaces `send_message`/`receive_message` with calls to the
WhatsApp Business API webhook handlers; the orchestration call in the middle
does not change.

Run with:  python -m taura.channels.whatsapp_simulator
"""
from __future__ import annotations

import uuid

from ..orchestrator import Orchestrator

# A short scripted exchange standing in for real inbound WhatsApp webhooks.
SCRIPTED_CONVERSATION = [
    "Mhoro",
    "hongu",
    "mutengo wechibage muMutare",
    "kuzonaya here muGokwe",
    "ndinoda kuchengetedza mari",
]


def send_message(text: str) -> None:
    print(f"[WhatsApp -> Taura Business Number]: {text}")


def receive_message(text: str, escalated: bool) -> None:
    tag = " (handed to human agent)" if escalated else ""
    print(f"[Taura Business Number -> WhatsApp]: {text}{tag}\n")


def main() -> None:
    orchestrator = Orchestrator()
    session_id = str(uuid.uuid4())
    print("=" * 60)
    print(" Taura AI -- WhatsApp channel simulator (scripted demo)")
    print("=" * 60)
    for user_text in SCRIPTED_CONVERSATION:
        send_message(user_text)
        result = orchestrator.handle_turn(session_id, "whatsapp", user_text)
        receive_message(result.response_text, result.escalated)


if __name__ == "__main__":
    main()
