# Asset & Licensing Register

Per the Track 3 Development Terms of Reference's technical delivery
standards, this register lists every third-party and original asset in this
repository.

See [`OSI_LICENSED_ALTERNATIVES.md`](OSI_LICENSED_ALTERNATIVES.md) for the
full evaluation behind the ASR/TTS licensing entries below — what was
checked, what was ruled out, and why.

| Asset | Type | Licence / ownership | Notes |
|---|---|---|---|
| All source code in `src/`, `backend/`, `webapp/`, `tests/`, `scripts/` | Original | Team-owned; intended for open-source release (e.g. MIT, see `LICENSE`) | No third-party code copied in |
| `fastapi`, `uvicorn`, `pydantic`, `pytest`, `httpx` | Third-party Python package | Each under its own OSI-approved licence (MIT/Apache-2.0/BSD family) | Installed via `requirements.lock.txt`; see each package's PyPI page for its specific licence |
| `torch`, `transformers`, `soundfile`, `librosa`, `numpy` | Third-party Python package (optional) | BSD-3-Clause (torch, numpy), Apache-2.0 (transformers), BSD (soundfile, librosa) | Only needed for real ASR backends (`TAURA_ASR_BACKEND=mms` / `whisper_finetuned`); installed via `requirements-asr.txt`, not the core lockfile |
| `facebook/mms-1b-all` model weights | Third-party model checkpoint (not bundled) | **CC-BY-NC 4.0 (non-commercial only)**, confirmed via the official model card and Meta's fairseq MMS release notes | Downloaded from the Hugging Face Hub on first use of `MMSSpeechRecognizer`; not included in this repository. **This is a real constraint on the commercial/institutional-subscription sustainability model in Section 5 of the written proposal** — CC-BY-NC prohibits commercial use of the model itself. Before any paid pilot or production deployment, either (a) confirm with Meta whether the specific deployment counts as non-commercial (e.g. a public-interest/grant-funded pilot may qualify, per Creative Commons' NC guidance — this is a judgement call, not guaranteed), (b) fine-tune an OSI-licensed base model (e.g. `wav2vec2-xlsr` variants) on the pilot-site corpus instead, or (c) budget for a commercially-licensed ASR provider. Track this explicitly as a Milestone 1 risk item. |
| `facebook/wav2vec2-large-xlsr-53` base checkpoint | Third-party model checkpoint (not bundled) | **Apache-2.0 (commercial-safe)**, confirmed via the Hugging Face model card | Downloaded on first use of `XLSRSpeechRecognizer` once a fine-tuned checkpoint exists (no ready Shona/Ndebele checkpoint today — fine-tuning is required either way). See `docs/OSI_LICENSED_ALTERNATIVES.md` — this is the recommended commercial-safe ASR path. |
| Original VITS reference architecture (`jaywalnut310/vits`) | Third-party training code (not bundled), reference for the `custom_vits` TTS path | **MIT** | No pretrained weights are released by the original authors for any language — this is architecture/training-code only. Training your own checkpoint on the pilot voice corpus is a fully OSI-clean path with no third-party model license involved at all. See `docs/OSI_LICENSED_ALTERNATIVES.md`. |
| `facebook/mms-tts-<lang>` model weights | Third-party model checkpoint (not bundled) | **CC-BY-NC 4.0 (non-commercial only)**, same MMS release family and licensing as the ASR checkpoint above | Downloaded from the Hugging Face Hub on first use of `MMSTextToSpeech`; not included in this repository. Same commercial-use constraint and options as the MMS ASR row above — this is not a separate risk, it's the same one appearing twice because MMS ASR and MMS-TTS are both candidate components. **Note:** Coqui TTS's bundled `tts_models/<iso>/fairseq/vits` models are these same MMS checkpoints via a different loader — using Coqui's toolkit does not avoid this restriction, see `docs/OSI_LICENSED_ALTERNATIVES.md`. |
| Phrase-splicing audio clips (`data/audio_clips/`) | Original recordings (not yet made) | Team-owned, no third-party licence involved | The `TAURA_TTS_BACKEND=phrase_splicing` path has no licensing constraint at all — it plays back your own recordings under whatever consent/release the voice talent gives (see `data/audio_clips/README.md`). This is the licensing-clean fallback for the five fixed response templates if the MMS-TTS NC constraint proves blocking for a paid pilot. |
| `data/*.json` | Original, synthetic | Team-owned | Illustrative only -- see `docs/DATASET_STATEMENT.md`; not derived from any copyrighted dataset |
| Fonts referenced in `webapp/index.html` (Fraunces, IBM Plex Sans, IBM Plex Mono) | Third-party, loaded from Google Fonts at runtime | SIL Open Font License 1.1 | Not bundled in the repo; loaded client-side via `<link>` tag from `fonts.googleapis.com` |
| Base ASR/TTS/LLM models (not included) | Third-party, to be integrated post-selection | Depends on final provider choice (e.g. Meta MMS / Whisper family are typically Apache-2.0 or MIT; open-weight LLMs vary by release) | See `docs/ARCHITECTURE.md` "Why each stub exists" table |

## What is explicitly NOT included in this repository

- No audio model weights or checkpoints.
- No real AMA, ZIMSTAT, MSD, Civil Protection, or EcoCash/MFI data or
  credentials.
- No API keys or secrets of any kind (see `.env.example` for the variable
  names a production deployment would need).

## Recommended licence for this repository

A permissive open-source licence (MIT) is recommended so this can serve the
"local-language AI capability" goal referenced in Section 1.4 of the written
proposal -- see `LICENSE`.
