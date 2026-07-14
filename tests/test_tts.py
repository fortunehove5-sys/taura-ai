import json
import wave
from pathlib import Path

import pytest

from taura import config
from taura.tts import (
    MMSTextToSpeech,
    PassthroughTTS,
    PhraseSplicingTTS,
    get_speech_synthesizer,
)


def test_passthrough_is_default_backend():
    original = config.TTS_BACKEND
    config.TTS_BACKEND = "passthrough"
    try:
        tts = get_speech_synthesizer()
        assert isinstance(tts, PassthroughTTS)
        result = tts.synthesize("mhoro", "sn")
        assert result.text == "mhoro"
        assert result.audio_bytes is None
        assert result.source == "passthrough"
    finally:
        config.TTS_BACKEND = original


def test_factory_selects_mms_backend():
    original = config.TTS_BACKEND
    config.TTS_BACKEND = "mms"
    try:
        assert isinstance(get_speech_synthesizer(), MMSTextToSpeech)
    finally:
        config.TTS_BACKEND = original


def test_factory_selects_phrase_splicing_backend():
    original = config.TTS_BACKEND
    config.TTS_BACKEND = "phrase_splicing"
    try:
        assert isinstance(get_speech_synthesizer(), PhraseSplicingTTS)
    finally:
        config.TTS_BACKEND = original


def test_factory_selects_custom_vits_backend_when_model_id_configured():
    original_backend = config.TTS_BACKEND
    original_model_id = config.TTS_CUSTOM_VITS_MODEL_ID
    config.TTS_BACKEND = "custom_vits"
    config.TTS_CUSTOM_VITS_MODEL_ID = "some-org/my-finetuned-shona-vits"
    try:
        tts = get_speech_synthesizer()
        assert isinstance(tts, MMSTextToSpeech)
        assert tts.model_id_template == "some-org/my-finetuned-shona-vits"
    finally:
        config.TTS_BACKEND = original_backend
        config.TTS_CUSTOM_VITS_MODEL_ID = original_model_id


def test_custom_vits_backend_requires_model_id():
    original_backend = config.TTS_BACKEND
    original_model_id = config.TTS_CUSTOM_VITS_MODEL_ID
    config.TTS_BACKEND = "custom_vits"
    config.TTS_CUSTOM_VITS_MODEL_ID = ""
    try:
        with pytest.raises(RuntimeError, match="TAURA_TTS_CUSTOM_VITS_MODEL_ID"):
            get_speech_synthesizer()
    finally:
        config.TTS_BACKEND = original_backend
        config.TTS_CUSTOM_VITS_MODEL_ID = original_model_id


def test_factory_rejects_unknown_backend():
    original = config.TTS_BACKEND
    config.TTS_BACKEND = "not_a_real_backend"
    try:
        with pytest.raises(ValueError):
            get_speech_synthesizer()
    finally:
        config.TTS_BACKEND = original


def test_mms_tts_gives_clear_error_without_optional_deps():
    tts = MMSTextToSpeech()
    with pytest.raises(RuntimeError):
        tts.synthesize("mhoro", "sn")


def test_phrase_splicing_requires_a_manifest():
    tts = PhraseSplicingTTS(manifest_path="/nonexistent/manifest.json")
    with pytest.raises(RuntimeError, match="clip manifest"):
        tts.synthesize("mhoro", "sn")


def _write_wav(path: Path, seconds: float = 0.05, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n_frames = int(seconds * sample_rate)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n_frames)


@pytest.fixture
def manifest_with_one_clip(tmp_path):
    """A minimal manifest + real recorded clip, isolated in a tmp dir so this
    test never touches the repo's real data/audio_clips_manifest.json."""
    clip_rel_path = "audio_clips/sn/TEST-GREETING.wav"
    _write_wav(tmp_path / clip_rel_path)

    manifest = {
        "clips": {
            "sn": {
                "Mhoro": {"file": clip_rel_path, "source_id": "TEST-GREETING", "status": "recorded"},
            },
            "nd": {},
            "en": {},
        }
    }
    manifest_path = tmp_path / "audio_clips_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    return manifest_path


def test_phrase_splicing_plays_back_matching_clip(manifest_with_one_clip):
    tts = PhraseSplicingTTS(manifest_path=str(manifest_with_one_clip))
    result = tts.synthesize("Mhoro", "sn")
    assert result.audio_bytes is not None
    assert result.source == "clip:audio_clips/sn/TEST-GREETING.wav"


def test_phrase_splicing_falls_back_for_unmatched_text(manifest_with_one_clip):
    """A price response (variable data) has no fixed clip -- must fall back
    to text-only rather than erroring."""
    tts = PhraseSplicingTTS(manifest_path=str(manifest_with_one_clip))
    result = tts.synthesize("Mutengo wechibage munoMutare ndeve $14.50", "sn")
    assert result.audio_bytes is None
    assert result.source == "passthrough"


def test_phrase_splicing_falls_back_when_clip_file_missing(tmp_path):
    """Manifest lists an entry but the recording hasn't been made yet
    (status: missing) -- must fall back gracefully, not crash."""
    manifest = {
        "clips": {
            "sn": {
                "Mhoro": {"file": "audio_clips/sn/NOT-YET-RECORDED.wav", "source_id": "X", "status": "missing"},
            },
            "nd": {},
            "en": {},
        }
    }
    manifest_path = tmp_path / "audio_clips_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    tts = PhraseSplicingTTS(manifest_path=str(manifest_path))
    result = tts.synthesize("Mhoro", "sn")
    assert result.audio_bytes is None
    assert result.source == "passthrough"
