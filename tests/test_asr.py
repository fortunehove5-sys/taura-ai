import pytest

from taura import config
from taura.asr import (
    MMSSpeechRecognizer,
    PassthroughASR,
    WhisperFineTunedASR,
    XLSRSpeechRecognizer,
    get_speech_recognizer,
)


def test_passthrough_is_default_backend():
    original = config.ASR_BACKEND
    config.ASR_BACKEND = "passthrough"
    try:
        recognizer = get_speech_recognizer()
        assert isinstance(recognizer, PassthroughASR)
        assert recognizer.transcribe("mhoro".encode("utf-8")) == "mhoro"
    finally:
        config.ASR_BACKEND = original


def test_factory_selects_mms_backend():
    original = config.ASR_BACKEND
    config.ASR_BACKEND = "mms"
    try:
        recognizer = get_speech_recognizer()
        assert isinstance(recognizer, MMSSpeechRecognizer)
    finally:
        config.ASR_BACKEND = original


def test_factory_selects_whisper_finetuned_backend():
    original = config.ASR_BACKEND
    config.ASR_BACKEND = "whisper_finetuned"
    try:
        recognizer = get_speech_recognizer()
        assert isinstance(recognizer, WhisperFineTunedASR)
    finally:
        config.ASR_BACKEND = original


def test_factory_selects_xlsr_finetuned_backend():
    original = config.ASR_BACKEND
    config.ASR_BACKEND = "xlsr_finetuned"
    try:
        recognizer = get_speech_recognizer()
        assert isinstance(recognizer, XLSRSpeechRecognizer)
    finally:
        config.ASR_BACKEND = original


def test_factory_rejects_unknown_backend():
    original = config.ASR_BACKEND
    config.ASR_BACKEND = "not_a_real_backend"
    try:
        with pytest.raises(ValueError):
            get_speech_recognizer()
    finally:
        config.ASR_BACKEND = original


def test_mms_backend_gives_clear_error_without_optional_deps_or_when_offline():
    """This environment intentionally does not install torch/transformers
    (see requirements-asr.txt) -- confirm the failure mode is a clear,
    actionable RuntimeError rather than a raw ImportError traceback, whether
    the failure is a missing package or (once installed) a blocked download.
    """
    recognizer = MMSSpeechRecognizer()
    with pytest.raises(RuntimeError):
        recognizer.transcribe(b"fake-audio-bytes")


def test_whisper_finetuned_backend_requires_model_path():
    original = config.ASR_WHISPER_MODEL_PATH
    config.ASR_WHISPER_MODEL_PATH = ""
    try:
        recognizer = WhisperFineTunedASR()
        with pytest.raises(RuntimeError, match="TAURA_ASR_WHISPER_MODEL_PATH"):
            recognizer.transcribe(b"fake-audio-bytes")
    finally:
        config.ASR_WHISPER_MODEL_PATH = original


def test_xlsr_finetuned_backend_requires_model_path():
    original = config.ASR_XLSR_MODEL_PATH
    config.ASR_XLSR_MODEL_PATH = ""
    try:
        recognizer = XLSRSpeechRecognizer()
        with pytest.raises(RuntimeError, match="TAURA_ASR_XLSR_MODEL_PATH"):
            recognizer.transcribe(b"fake-audio-bytes")
    finally:
        config.ASR_XLSR_MODEL_PATH = original
