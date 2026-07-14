"""Central orchestration pipeline.

Implements the flow from the architecture diagram in the written proposal:

    channel input -> ASR (transcribe) -> language hint -> consent check
    -> intent classification -> entity extraction -> RAG retrieval
    -> response generation -> TTS ("synthesize") -> audit log -> channel output

Every channel simulator (CLI, WhatsApp, USSD) and the FastAPI web backend call
the same `Orchestrator.handle_turn()` method, so behaviour is identical across
channels -- only the transport differs, exactly as described in Section 2.2 of
the written proposal ("reusing the same backend").
"""
from __future__ import annotations

from dataclasses import dataclass

from . import audit_log
from .asr import get_speech_recognizer
from . import config
from .consent import ConsentStatus, ConsentStore
from .entity_extractor import extract as extract_entities
from .intent_classifier import Intent, classify
from .language_detector import detect as detect_language
from .rag_retriever import RagRetriever
from .response_generator import get_response_generator
from .tts import get_speech_synthesizer

# Fixed, variable-free template -- deliberately a plain module constant (not
# loaded from data/knowledge_base.json like the other fixed messages) since
# it's purely a consent-flow acknowledgement, not a "grounded" answer. Kept
# as a named constant so it can be reused verbatim elsewhere (e.g.
# scripts/generate_clip_manifest.py) without copy-pasting the strings.
CONSENT_DECLINE_MESSAGES = {
    "sn": "Zvakanaka, hatichazochengetedzi ruzivo rwehurukuro ino. Unogona kudzoka chero nguva.",
    "nd": "Kulungile, kasisoze sagcina ulwazi lwalesisikhulumo. Ungabuya nini lanini.",
    "en": "Understood, we will not store this conversation. You can return any time.",
}


@dataclass
class TurnResult:
    session_id: str
    channel: str
    language: str
    intent: str
    response_text: str
    escalated: bool
    retrieved_source_id: str | None = None


class Orchestrator:
    def __init__(self) -> None:
        self.retriever = RagRetriever()
        self.responder = get_response_generator(config.RESPONSE_BACKEND)
        self.asr = get_speech_recognizer()
        self.tts = get_speech_synthesizer()
        self.consent_store = ConsentStore()

    def handle_turn(self, session_id: str, channel: str, raw_input: bytes | str) -> TurnResult:
        """Process one turn of a conversation and return the response to play/show.

        `raw_input` may be raw audio bytes (voice channel) or a plain string
        (USSD/WhatsApp text, or the CLI/web demo). Both paths go through the
        same ASR interface -- PassthroughASR treats strings as already-decoded
        text and bytes as UTF-8-encoded text, so the pipeline is exercised
        identically regardless of input type.
        """
        if isinstance(raw_input, bytes):
            text = self.asr.transcribe(raw_input)
        else:
            text = self.asr.transcribe(raw_input.encode("utf-8"))

        language = detect_language(text)
        classification = classify(text)
        intent = classification.intent

        # -- Consent gate -----------------------------------------------
        if config.REQUIRE_CONSENT and not self.consent_store.is_resolved(session_id):
            if intent == Intent.CONSENT_YES:
                self.consent_store.grant(session_id)
                greeting = self.retriever.find_knowledge("greeting")
                response_text = self.responder.phrase_knowledge(greeting, language) if greeting else ""
                audit_log.new_entry(session_id, channel, language, ConsentStatus.GRANTED.value,
                                     intent.value, greeting.source_id if greeting else None, "answered")
                return TurnResult(session_id, channel, language, intent.value, response_text, False,
                                   greeting.source_id if greeting else None)

            if intent == Intent.CONSENT_NO:
                self.consent_store.decline(session_id)
                response_text = CONSENT_DECLINE_MESSAGES.get(
                    language, CONSENT_DECLINE_MESSAGES["en"]
                )
                audit_log.new_entry(session_id, channel, language, ConsentStatus.DECLINED.value,
                                     intent.value, None, "declined_no_consent")
                return TurnResult(session_id, channel, language, intent.value, response_text, False, None)

            # Consent not yet resolved and this turn isn't a yes/no reply:
            # ask for consent instead of answering anything substantive.
            consent_prompt = self.retriever.find_knowledge("consent_prompt")
            response_text = self.responder.phrase_knowledge(consent_prompt, language) if consent_prompt else ""
            audit_log.new_entry(session_id, channel, language, ConsentStatus.UNKNOWN.value,
                                 "consent_prompt", consent_prompt.source_id if consent_prompt else None,
                                 "awaiting_consent")
            return TurnResult(session_id, channel, language, "consent_prompt", response_text, False,
                               consent_prompt.source_id if consent_prompt else None)

        # -- Routing after consent is resolved (or not required) --------
        entities = extract_entities(text)
        escalated = False
        retrieved_id = None

        if intent == Intent.GREETING:
            record = self.retriever.find_knowledge("greeting")
            response_text = self.responder.phrase_knowledge(record, language) if record else ""
            retrieved_id = record.source_id if record else None
            outcome = "answered"

        elif intent == Intent.PRICE_QUERY:
            record = self.retriever.find_price(entities)
            if record:
                response_text = self.responder.phrase_price(record, language)
                retrieved_id = record.source_id
                outcome = "answered"
            else:
                response_text = self.responder.no_data_found(language)
                outcome = "no_data_found"

        elif intent == Intent.CLIMATE_QUERY:
            record = self.retriever.find_climate_alert(entities)
            if record:
                response_text = self.responder.phrase_climate(record, language)
                retrieved_id = record.source_id
                outcome = "answered"
            else:
                response_text = self.responder.no_data_found(language)
                outcome = "no_data_found"

        elif intent == Intent.FINANCIAL_QUERY:
            records = self.retriever.find_financial_products()
            response_text = self.responder.phrase_financial(records, language)
            retrieved_id = ",".join(r.source_id for r in records) if records else None
            # Any financial product requiring human sign-off triggers escalation,
            # matching the "AI never completes a financial transaction" rule
            # in Section 4.2 of the written proposal.
            escalated = any(r.data.get("human_handoff_required") for r in records)
            outcome = "escalated" if escalated else "answered"

        elif intent == Intent.HUMAN_HANDOFF:
            record = self.retriever.find_knowledge("human_handoff")
            response_text = self.responder.phrase_knowledge(record, language) if record else ""
            retrieved_id = record.source_id if record else None
            escalated = True
            outcome = "escalated"

        else:  # UNKNOWN or bare CONSENT_YES/NO outside a consent prompt
            response_text = self.responder.no_data_found(language)
            outcome = "unknown_intent"

        consent_status = self.consent_store.get(session_id).value if config.REQUIRE_CONSENT else "not_required"
        audit_log.new_entry(session_id, channel, language, consent_status, intent.value, retrieved_id, outcome)

        # "TTS" -- in the offline demo this is a passthrough; a real deployment
        # would play back synthesized_speech.audio_bytes on the voice channel.
        synthesized_speech = self.tts.synthesize(response_text, language)

        return TurnResult(
            session_id=session_id,
            channel=channel,
            language=language,
            intent=intent.value,
            response_text=synthesized_speech.text,
            escalated=escalated,
            retrieved_source_id=retrieved_id,
        )
