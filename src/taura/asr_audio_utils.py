"""Audio decoding helpers for real ASR backends.

Kept separate from asr.py so that importing `taura.asr` for the default
PassthroughASR path never requires numpy/soundfile to be installed. These
helpers are only imported lazily, inside the real backends in asr.py, at the
point they are actually used.

Requires the optional `requirements-asr.txt` extras (numpy, soundfile,
librosa). Install with:

    pip install -r requirements-asr.txt
"""
from __future__ import annotations

import io

TARGET_SAMPLE_RATE = 16_000  # both MMS and Whisper expect 16kHz mono audio


def load_audio_as_array(audio_bytes: bytes):
    """Decode arbitrary audio bytes (wav/flac/ogg -- whatever soundfile
    supports) into a mono float32 numpy array at TARGET_SAMPLE_RATE.

    Raises a clear RuntimeError (not a raw ImportError traceback) if the
    optional audio dependencies are not installed.
    """
    try:
        import numpy as np
        import soundfile as sf
    except ImportError as exc:
        raise RuntimeError(
            "Real ASR backends need the optional audio dependencies. Install "
            "them with:\n    pip install -r requirements-asr.txt"
        ) from exc

    data, sample_rate = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=False)

    # Downmix to mono if the source audio has multiple channels.
    if data.ndim > 1:
        data = data.mean(axis=1)

    if sample_rate != TARGET_SAMPLE_RATE:
        data = _resample(data, sample_rate, TARGET_SAMPLE_RATE)

    return data


def _resample(data, orig_sr: int, target_sr: int):
    try:
        import librosa
    except ImportError as exc:
        raise RuntimeError(
            "Resampling audio to 16kHz needs librosa. Install it with:\n"
            "    pip install -r requirements-asr.txt"
        ) from exc
    return librosa.resample(data, orig_sr=orig_sr, target_sr=target_sr)
