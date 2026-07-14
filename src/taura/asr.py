"""Automatic Speech Recognition (ASR) integration point.

Four backends implement the shared `SpeechRecognizer` interface:

- `PassthroughASR` (default): treats `audio_bytes` as UTF-8 text. This is
  what the CLI/WhatsApp/USSD simulators and the web demo use, and it's what
  every automated test in this repo runs against -- no audio model, no
  network access, no GPU required. Select with TAURA_ASR_BACKEND=passthrough
  (the default).

- `MMSSpeechRecognizer`: real wiring for Meta's Massively Multilingual Speech
  model (`facebook/mms-1b-all`), which covers Shona ("sna") and Zimbabwean
  Ndebele ("nde") via per-language adapter weights on top of a shared
  Wav2Vec2 backbone. Select with TAURA_ASR_BACKEND=mms.

  LICENSING WARNING: facebook/mms-1b-all is released under CC-BY-NC 4.0
  (non-commercial use only), confirmed via its Hugging Face model card and
  Meta's fairseq MMS release notes. This is a real constraint on the paid
  institutional-subscription sustainability model described in the written
  proposal (Section 5) -- see docs/ASSET_LICENSE_REGISTER.md and
  docs/OSI_LICENSED_ALTERNATIVES.md for the options (confirm non-commercial-
  use eligibility, fine-tune an OSI-licensed base model instead, or budget
  for a commercially-licensed ASR provider) before any paid pilot or
  production deployment.

- `WhisperFineTunedASR`: real wiring for a Whisper checkpoint fine-tuned on
  the consented pilot-site Shona/Ndebele voice corpus (base Whisper does not
  natively cover these languages, so this backend is only useful once such a
  fine-tune exists -- see docs/DATASET_STATEMENT.md). Whisper itself is
  MIT-licensed (commercial-safe). Select with TAURA_ASR_BACKEND=whisper_finetuned
  and TAURA_ASR_WHISPER_MODEL_PATH set to a local checkpoint directory or a
  private HF Hub repo id.

- `XLSRSpeechRecognizer`: real wiring for a wav2vec2-XLSR checkpoint
  fine-tuned the same way (Apache-2.0 base, also commercial-safe). See
  docs/OSI_LICENSED_ALTERNATIVES.md for why this is offered alongside
  Whisper rather than instead of it. Select with
  TAURA_ASR_BACKEND=xlsr_finetuned and TAURA_ASR_XLSR_MODEL_PATH.

Neither real backend is imported, downloaded, or loaded unless it is actually
selected and instantiated -- `taura.asr` itself has no heavy dependency, so
`import taura.orchestrator` (and every test in this repo) stays fast and
offline by default. The heavy deps (torch, transformers, soundfile, librosa)
live in the optional `requirements-asr.txt`, not the core `requirements.txt`.

Model weights are NOT bundled in this repository (see docs/ASSET_LICENSE_REGISTER.md).
Loading a real backend downloads the checkpoint from the Hugging Face Hub on
first use (or reads the relevant *_MODEL_PATH setting for the fine-tuned
cases) -- this requires network access and disk space that this sandboxed
submission environment does not have, so these classes are unit-tested for
correct wiring/error-handling only, not for real transcription accuracy. That
validation is the Milestone 1 deliverable described in the written proposal
(Section 3.1: "ASR/TTS accuracy benchmark on pilot-site voice sample").
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from . import config


class SpeechRecognizer(ABC):
    @abstractmethod
    def transcribe(self, audio_bytes: bytes) -> str:
        """Return the transcribed text for the given audio."""


class PassthroughASR(SpeechRecognizer):
    """Demo/testing stand-in: treats the 'audio_bytes' as UTF-8 encoded text.

    This lets the CLI simulators and the web chat demo exercise the full
    orchestration pipeline (intent -> retrieval -> response -> "TTS") without
    a real audio model, while keeping the SpeechRecognizer interface identical
    to what a real ASR integration would implement.
    """

    def transcribe(self, audio_bytes: bytes) -> str:
        return audio_bytes.decode("utf-8", errors="ignore")


class MMSSpeechRecognizer(SpeechRecognizer):
    """Meta MMS (facebook/mms-1b-all) ASR with a per-language adapter.

    This mirrors the documented Hugging Face integration for MMS: a single
    Wav2Vec2 backbone with small per-language adapter weights swapped in for
    the target language. Reference:
    https://huggingface.co/facebook/mms-1b-all

    The model and processor are loaded lazily on first `transcribe()` call
    (not at __init__), so constructing this object is cheap and only the
    actual transcription path requires the model to be resident in memory.
    """

    def __init__(self, model_id: str | None = None, language: str | None = None):
        self.model_id = model_id or config.ASR_MMS_MODEL_ID
        self.language = language or config.ASR_MMS_LANGUAGE
        self._model = None
        self._processor = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            from transformers import AutoProcessor, Wav2Vec2ForCTC
        except ImportError as exc:
            raise RuntimeError(
                "MMSSpeechRecognizer needs transformers + torch. Install "
                "with:\n    pip install -r requirements-asr.txt"
            ) from exc

        # target_lang selects which adapter head to attach; ignore_mismatched_sizes
        # is required because the adapter's output vocabulary differs per language.
        self._processor = AutoProcessor.from_pretrained(self.model_id, target_lang=self.language)
        self._model = Wav2Vec2ForCTC.from_pretrained(
            self.model_id, target_lang=self.language, ignore_mismatched_sizes=True
        )
        self._model.load_adapter(self.language)
        self._model.eval()

    def transcribe(self, audio_bytes: bytes) -> str:
        self._ensure_loaded()

        import torch

        from .asr_audio_utils import load_audio_as_array

        audio_array = load_audio_as_array(audio_bytes)
        inputs = self._processor(audio_array, sampling_rate=16_000, return_tensors="pt")

        with torch.no_grad():
            logits = self._model(**inputs).logits

        predicted_ids = torch.argmax(logits, dim=-1)[0]
        return self._processor.decode(predicted_ids)


class XLSRSpeechRecognizer(SpeechRecognizer):
    """A wav2vec2-XLSR checkpoint fine-tuned on the consented pilot-site voice corpus.

    Evaluated in docs/OSI_LICENSED_ALTERNATIVES.md as the recommended
    OSI-licensed (Apache-2.0 base) alternative to MMS ASR: no ready-made
    Shona/Ndebele checkpoint exists for this architecture either, but the
    base model (`facebook/wav2vec2-large-xlsr-53`) carries no commercial-use
    restriction, unlike MMS. This class mirrors WhisperFineTunedASR's
    pattern -- it requires a fine-tuned checkpoint path and fails clearly if
    one isn't configured, rather than silently falling back to anything.

    Why this exists alongside WhisperFineTunedASR rather than replacing it:
    CTC architectures like XLSR are generally reported to need less labelled
    fine-tuning data than Whisper's full seq2seq decoder to reach usable
    accuracy on a new low-resource language, and the base model is smaller
    (315M vs. Whisper large's 1.5B params) -- relevant given the pilot-site
    corpus will start small and GPU availability is an open item (see
    deploy/zchpc/VM_SIZING.md). Milestone 1's ASR benchmark should test both
    and report which performs better on Shona/Ndebele specifically, rather
    than committing to one now on generic reasoning alone.
    """

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or config.ASR_XLSR_MODEL_PATH
        self._model = None
        self._processor = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        if not self.model_path:
            raise RuntimeError(
                "XLSRSpeechRecognizer requires TAURA_ASR_XLSR_MODEL_PATH to "
                "point at a fine-tuned checkpoint (local directory or HF Hub "
                "repo id). No fine-tuned Shona/Ndebele checkpoint exists yet "
                "-- this is a Milestone 1 deliverable (see written proposal, "
                "Section 3.1, and docs/OSI_LICENSED_ALTERNATIVES.md)."
            )
        try:
            from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
        except ImportError as exc:
            raise RuntimeError(
                "XLSRSpeechRecognizer needs transformers + torch. Install "
                "with:\n    pip install -r requirements-asr.txt"
            ) from exc

        self._processor = Wav2Vec2Processor.from_pretrained(self.model_path)
        self._model = Wav2Vec2ForCTC.from_pretrained(self.model_path)
        self._model.eval()

    def transcribe(self, audio_bytes: bytes) -> str:
        self._ensure_loaded()

        import torch

        from .asr_audio_utils import load_audio_as_array

        audio_array = load_audio_as_array(audio_bytes)
        inputs = self._processor(audio_array, sampling_rate=16_000, return_tensors="pt")

        with torch.no_grad():
            logits = self._model(**inputs).logits

        predicted_ids = torch.argmax(logits, dim=-1)
        return self._processor.batch_decode(predicted_ids)[0]


class WhisperFineTunedASR(SpeechRecognizer):
    """A Whisper checkpoint fine-tuned on the consented pilot-site voice corpus.

    Base/off-the-shelf Whisper does not natively cover Shona or Ndebele, so
    this backend is only meaningful once a fine-tuned checkpoint exists (see
    the Milestone 1 ASR benchmark in the written proposal, Section 3.1). Point
    TAURA_ASR_WHISPER_MODEL_PATH at that checkpoint (a local directory, or a
    private Hugging Face Hub repo id) before selecting this backend.
    """

    def __init__(self, model_path: str | None = None, language_hint: str | None = None):
        self.model_path = model_path or config.ASR_WHISPER_MODEL_PATH
        self.language_hint = language_hint  # e.g. "sn" or "nd"; None = auto
        self._model = None
        self._processor = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        if not self.model_path:
            raise RuntimeError(
                "WhisperFineTunedASR requires TAURA_ASR_WHISPER_MODEL_PATH to "
                "point at a fine-tuned checkpoint (local directory or HF Hub "
                "repo id). No fine-tuned Shona/Ndebele checkpoint exists yet "
                "-- this is a Milestone 1 deliverable (see written proposal, "
                "Section 3.1)."
            )
        try:
            from transformers import WhisperForConditionalGeneration, WhisperProcessor
        except ImportError as exc:
            raise RuntimeError(
                "WhisperFineTunedASR needs transformers + torch. Install "
                "with:\n    pip install -r requirements-asr.txt"
            ) from exc

        self._processor = WhisperProcessor.from_pretrained(self.model_path)
        self._model = WhisperForConditionalGeneration.from_pretrained(self.model_path)
        self._model.eval()

    def transcribe(self, audio_bytes: bytes) -> str:
        self._ensure_loaded()

        import torch

        from .asr_audio_utils import load_audio_as_array

        audio_array = load_audio_as_array(audio_bytes)
        inputs = self._processor(audio_array, sampling_rate=16_000, return_tensors="pt")

        forced_decoder_ids = None
        if self.language_hint:
            # Whisper's language tag uses its own two-letter codes; a
            # genuinely fine-tuned checkpoint for Shona/Ndebele may register
            # custom language tokens during fine-tuning -- confirm the exact
            # tag your fine-tune used rather than assuming this maps directly.
            forced_decoder_ids = self._processor.get_decoder_prompt_ids(
                language=self.language_hint, task="transcribe"
            )

        with torch.no_grad():
            predicted_ids = self._model.generate(
                inputs["input_features"], forced_decoder_ids=forced_decoder_ids
            )

        return self._processor.batch_decode(predicted_ids, skip_special_tokens=True)[0].strip()


def get_speech_recognizer() -> SpeechRecognizer:
    backend = config.ASR_BACKEND
    if backend == "mms":
        return MMSSpeechRecognizer()
    if backend == "whisper_finetuned":
        return WhisperFineTunedASR()
    if backend == "xlsr_finetuned":
        return XLSRSpeechRecognizer()
    if backend != "passthrough":
        raise ValueError(
            f"Unknown TAURA_ASR_BACKEND={backend!r}. Expected one of: "
            "'passthrough', 'mms', 'whisper_finetuned', 'xlsr_finetuned'."
        )
    return PassthroughASR()
