"""Text-to-Speech (TTS) integration point.

Four backends implement the shared `SpeechSynthesizer` interface:

- `PassthroughTTS` (default): returns the text unchanged, no audio. Used by
  the CLI/WhatsApp/USSD simulators and the web demo, and by every automated
  test -- no audio model, no recordings, no network access required. Select
  with TAURA_TTS_BACKEND=passthrough (the default).

- `MMSTextToSpeech`: real wiring for Meta's MMS-TTS family
  (`facebook/mms-tts-<lang>`, one checkpoint per language -- `sna` for Shona,
  `nde` for Zimbabwean/North Ndebele), via `transformers.VitsModel`. Select
  with TAURA_TTS_BACKEND=mms.

  LICENSING WARNING: like MMS ASR, MMS-TTS checkpoints are released under
  CC-BY-NC 4.0 (non-commercial use only), confirmed via the Hugging Face
  model cards for facebook/mms-tts-eng and sibling per-language checkpoints,
  and Meta's fairseq MMS release notes. The same constraint on the paid
  institutional-subscription sustainability model applies here as for ASR --
  see docs/ASSET_LICENSE_REGISTER.md and docs/OSI_LICENSED_ALTERNATIVES.md
  before any paid pilot or production use.

- `custom_vits` backend (same `MMSTextToSpeech` class, different config):
  points the identical VitsModel wiring at a self-trained checkpoint via
  TAURA_TTS_CUSTOM_VITS_MODEL_ID instead of Meta's NC-licensed
  `facebook/mms-tts-{lang}` template. This is the OSI-clean path evaluated in
  docs/OSI_LICENSED_ALTERNATIVES.md: train your own VITS model (MIT-licensed
  reference architecture) on the same consented pilot-site voice corpus
  planned for ASR fine-tuning. No ready-made checkpoint exists for this yet
  -- selecting this backend without setting the model id raises a clear
  error rather than silently falling back to anything.

- `PhraseSplicingTTS`: the "pre-recorded fallback for top intents" mitigation
  named explicitly in the written proposal (Section 4.5, TTS quality risk).
  Plays back a pre-recorded audio clip for a response text that exactly
  matches one of the FIXED (variable-free) templates in
  data/knowledge_base.json -- greeting, consent prompt, human handoff, and
  the "no data found" fallback. It does NOT cover price/climate/financial
  responses, which contain variable data (a dollar figure, a location, a
  week number) that a fixed clip can't represent; those still need a real
  TTS backend, or a future number/commodity clip-concatenation extension
  (documented as a next step below, not implemented here). No licensing
  constraint applies to this backend -- it plays back your own recordings.

Neither real backend is imported, downloaded, or loaded unless it is
selected and instantiated -- `taura.tts` itself has no heavy dependency, so
the default path stays fast and offline. Heavy deps live in the optional
`requirements-asr.txt` (shared with the ASR backends -- same transformers
install covers both).
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from . import config


@dataclass
class SynthesizedSpeech:
    text: str
    language: str
    audio_bytes: bytes | None = None  # None when no audio was produced
    source: str = "passthrough"  # which backend/clip produced this, for the audit trail


class SpeechSynthesizer(ABC):
    @abstractmethod
    def synthesize(self, text: str, language: str) -> SynthesizedSpeech: ...


class PassthroughTTS(SpeechSynthesizer):
    def synthesize(self, text: str, language: str) -> SynthesizedSpeech:
        return SynthesizedSpeech(text=text, language=language, audio_bytes=None, source="passthrough")


class MMSTextToSpeech(SpeechSynthesizer):
    """Meta MMS-TTS (facebook/mms-tts-<lang>) via transformers.VitsModel.

    One checkpoint per language -- there is no single multilingual MMS-TTS
    model, unlike MMS ASR's shared backbone with per-language adapters.
    Checkpoints are loaded lazily and cached per language on first use.
    """

    def __init__(self, model_id_template: str | None = None):
        self.model_id_template = model_id_template or config.TTS_MMS_MODEL_ID_TEMPLATE
        self._models: dict[str, object] = {}
        self._tokenizers: dict[str, object] = {}

    def _ensure_loaded(self, language: str) -> None:
        if language in self._models:
            return
        try:
            from transformers import AutoTokenizer, VitsModel
        except ImportError as exc:
            raise RuntimeError(
                "MMSTextToSpeech needs transformers + torch. Install with:\n"
                "    pip install -r requirements-asr.txt"
            ) from exc

        model_id = self.model_id_template.format(lang=language)
        try:
            model = VitsModel.from_pretrained(model_id)
            tokenizer = AutoTokenizer.from_pretrained(model_id)
        except OSError as exc:
            raise RuntimeError(
                f"Could not load MMS-TTS checkpoint '{model_id}'. Confirm this "
                "language has a published MMS-TTS checkpoint, and that this "
                "environment has network access to the Hugging Face Hub on "
                "first use."
            ) from exc

        model.eval()
        self._models[language] = model
        self._tokenizers[language] = tokenizer

    def synthesize(self, text: str, language: str) -> SynthesizedSpeech:
        self._ensure_loaded(language)

        import torch

        model = self._models[language]
        tokenizer = self._tokenizers[language]

        inputs = tokenizer(text, return_tensors="pt")
        with torch.no_grad():
            output = model(**inputs).waveform

        wav_bytes = _waveform_to_wav_bytes(output.squeeze().cpu().numpy(), model.config.sampling_rate)
        return SynthesizedSpeech(text=text, language=language, audio_bytes=wav_bytes, source=f"mms:{language}")


def _waveform_to_wav_bytes(waveform, sample_rate: int) -> bytes:
    try:
        import io

        import numpy as np
        from scipy.io import wavfile
    except ImportError as exc:
        raise RuntimeError(
            "Encoding MMS-TTS output to WAV needs numpy + scipy. Install "
            "with:\n    pip install -r requirements-asr.txt"
        ) from exc

    buf = io.BytesIO()
    # VitsModel outputs float32 in [-1, 1]; scale to 16-bit PCM for a
    # standard, widely-playable WAV file.
    pcm16 = (np.clip(waveform, -1.0, 1.0) * 32767).astype(np.int16)
    wavfile.write(buf, sample_rate, pcm16)
    return buf.getvalue()


class PhraseSplicingTTS(SpeechSynthesizer):
    """Pre-recorded clip playback for fixed, variable-free response templates.

    Looks up the exact response `text` in a manifest (see
    data/audio_clips/README.md and scripts/generate_clip_manifest.py) mapping
    (language, text) -> a recorded audio file. This works because the fixed
    knowledge-base messages (greeting, consent prompt, human handoff,
    no-data-found) are deterministic, enumerable strings -- there's no need
    to splice at the word level for these.

    Falls back to passthrough behaviour (text only, no audio) for any text
    not in the manifest -- notably every price/climate/financial response,
    which contains variable data a fixed clip can't represent. This is a
    documented, honest limitation, not a bug: see the module docstring above.
    """

    def __init__(self, manifest_path: str | None = None):
        self.manifest_path = Path(manifest_path or config.TTS_CLIP_MANIFEST_PATH)
        self._manifest: dict | None = None

    def _load_manifest(self) -> dict:
        if self._manifest is not None:
            return self._manifest
        if not self.manifest_path.exists():
            raise RuntimeError(
                f"No clip manifest found at {self.manifest_path}. Generate one "
                "with: python scripts/generate_clip_manifest.py -- see "
                "data/audio_clips/README.md for the recording process."
            )
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            self._manifest = json.load(f)
        return self._manifest

    def synthesize(self, text: str, language: str) -> SynthesizedSpeech:
        manifest = self._load_manifest()
        entry = manifest.get("clips", {}).get(language, {}).get(text)

        if entry is None:
            # Not a fixed template (e.g. a price/climate response with
            # variable data) -- fall back gracefully rather than failing the
            # whole turn. See class docstring.
            return SynthesizedSpeech(text=text, language=language, audio_bytes=None, source="passthrough")

        clip_path = self.manifest_path.parent / entry["file"]
        if not clip_path.exists():
            # Manifest lists the expected clip but recording hasn't happened
            # yet (see scripts/generate_clip_manifest.py's "missing" status) --
            # same graceful fallback, not a crash.
            return SynthesizedSpeech(text=text, language=language, audio_bytes=None, source="passthrough")

        with open(clip_path, "rb") as f:
            audio_bytes = f.read()
        return SynthesizedSpeech(
            text=text, language=language, audio_bytes=audio_bytes, source=f"clip:{entry['file']}"
        )


def get_speech_synthesizer() -> SpeechSynthesizer:
    backend = config.TTS_BACKEND
    if backend == "mms":
        return MMSTextToSpeech()
    if backend == "custom_vits":
        if not config.TTS_CUSTOM_VITS_MODEL_ID:
            raise RuntimeError(
                "TTS_BACKEND=custom_vits requires TAURA_TTS_CUSTOM_VITS_MODEL_ID "
                "to point at a self-trained VITS checkpoint (local directory or "
                "HF Hub repo id). See docs/OSI_LICENSED_ALTERNATIVES.md."
            )
        # Reuses MMSTextToSpeech's VitsModel wiring verbatim -- the class is
        # architecture-generic, not Meta-specific. See its docstring and
        # docs/OSI_LICENSED_ALTERNATIVES.md for why this is offered as a
        # distinctly-named backend rather than silently overloading "mms".
        return MMSTextToSpeech(model_id_template=config.TTS_CUSTOM_VITS_MODEL_ID)
    if backend == "phrase_splicing":
        return PhraseSplicingTTS()
    if backend != "passthrough":
        raise ValueError(
            f"Unknown TAURA_TTS_BACKEND={backend!r}. Expected one of: "
            "'passthrough', 'mms', 'custom_vits', 'phrase_splicing'."
        )
    return PassthroughTTS()
