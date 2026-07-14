"""Interactive command-line chat channel.

Run with:  python -m taura.channels.cli_chat

Simulates a single ongoing session (as a phone call would be), routed through
the same Orchestrator used by the WhatsApp/USSD simulators and the web demo.
"""
from __future__ import annotations

import uuid

from ..orchestrator import Orchestrator


def main() -> None:
    orchestrator = Orchestrator()
    session_id = str(uuid.uuid4())
    print("=" * 60)
    print(" Taura AI -- CLI voice-call simulator")
    print(" Type a message in Shona, Ndebele or English. Ctrl+C to quit.")
    print(" Try: 'mhoro', 'mutengo wemaize muMutare', 'is it going to rain in Gokwe'")
    print("=" * 60)
    try:
        while True:
            user_text = input("\nYou: ").strip()
            if not user_text:
                continue
            result = orchestrator.handle_turn(session_id, "voice_call", user_text)
            tag = " [ESCALATED TO HUMAN AGENT]" if result.escalated else ""
            print(f"Taura ({result.language}): {result.response_text}{tag}")
    except (KeyboardInterrupt, EOFError):
        print("\nSession ended.")


if __name__ == "__main__":
    main()
