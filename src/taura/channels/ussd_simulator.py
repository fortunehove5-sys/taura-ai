"""USSD channel simulator.

Demonstrates a structured menu session (as a real *XXX# session would present)
that still routes free-text sub-menu replies through the same Orchestrator, so
a user who is more comfortable typing a short phrase than navigating menus
still reaches the identical AI pipeline used by voice and WhatsApp.

Run with:  python -m taura.channels.ussd_simulator
"""
from __future__ import annotations

import uuid

from ..orchestrator import Orchestrator

MENU = """
Taura AI - *888#
1. Mitengo yezviyo (Crop prices)
2. Mamiriro ekunze (Weather/flood alerts)
3. Mari nemakwereti (Savings/loans)
4. Taura nemunhu (Speak to a person)
0. Buda (Exit)
"""

# Maps a menu digit to a representative free-text query the Orchestrator can
# classify, since the real system accepts either a menu digit or typed text.
MENU_TO_QUERY = {
    "1": "mitengo yechibage muMutare",
    "2": "mamiriro ekunze muGokwe",
    "3": "ndinoda chikwereti",
    "4": "ndinoda kutaura nemunhu",
}


def main() -> None:
    orchestrator = Orchestrator()
    session_id = str(uuid.uuid4())
    print("=" * 60)
    print(" Taura AI -- USSD channel simulator")
    print("=" * 60)

    # Consent step first, as it would be on a real USSD session.
    consent_result = orchestrator.handle_turn(session_id, "ussd", "start")
    print(consent_result.response_text)
    consent_reply = input("Reply (YES/NO): ").strip() or "hongu"
    orchestrator.handle_turn(session_id, "ussd", consent_reply)

    try:
        while True:
            print(MENU)
            choice = input("Select option: ").strip()
            if choice == "0":
                print("Session ended.")
                break
            query = MENU_TO_QUERY.get(choice)
            if not query:
                print("Invalid option, please try again.")
                continue
            result = orchestrator.handle_turn(session_id, "ussd", query)
            tag = " [escalated to human agent]" if result.escalated else ""
            print(f"\n{result.response_text}{tag}\n")
    except (KeyboardInterrupt, EOFError):
        print("\nSession ended.")


if __name__ == "__main__":
    main()
