# Architecture

This document maps the architecture described in the written proposal
(`Taura_AI_Proposal_EDITABLE.docx`, Section 2) to the code in this
repository, so a reviewer can trace every box in the diagram to a concrete
module.

## Pipeline

```
channel input (voice / USSD / WhatsApp)
        |
        v
  ASR: transcribe()            src/taura/asr.py            (PassthroughASR stub; real ASR TODO)
        |
        v
  language hint: detect()      src/taura/language_detector.py
        |
        v
  consent gate                 src/taura/consent.py + orchestrator.py
        |
        v
  intent: classify()           src/taura/intent_classifier.py
        |
        v
  entities: extract()          src/taura/entity_extractor.py
        |
        v
  RAG retrieval: find_*()      src/taura/rag_retriever.py   (reads data/*.json)
        |
        v
  response generation          src/taura/response_generator.py
        |
        v
  TTS: synthesize()            src/taura/tts.py             (PassthroughTTS stub; real TTS TODO)
        |
        v
  audit log: new_entry()       src/taura/audit_log.py       (writes logs/audit.log)
        |
        v
channel output
```

Every channel simulator (`src/taura/channels/cli_chat.py`,
`whatsapp_simulator.py`, `ussd_simulator.py`) and the FastAPI backend
(`backend/app.py`) call the single entry point
`Orchestrator.handle_turn(session_id, channel, raw_input)`, so behaviour is
identical across channels -- only the transport wrapper differs.

## Why each stub exists, and how to replace it

| Component | File | Status | How to activate |
|---|---|---|---|
| ASR | `src/taura/asr.py` | **Real wiring implemented** for Meta MMS (`facebook/mms-1b-all`, adapters `sna`/`nde`, CC-BY-NC 4.0), a fine-tuned Whisper checkpoint (MIT base), and a fine-tuned wav2vec2-XLSR checkpoint (Apache-2.0 base). None has been run against real audio in this environment (no network access to the Hugging Face Hub, no GPU) -- see `docs/DATASET_STATEMENT.md` and `docs/OSI_LICENSED_ALTERNATIVES.md`. | `TAURA_ASR_BACKEND=mms`, `whisper_finetuned` (+ `TAURA_ASR_WHISPER_MODEL_PATH`), or `xlsr_finetuned` (+ `TAURA_ASR_XLSR_MODEL_PATH`) |
| TTS | `src/taura/tts.py` | **Real wiring implemented** for Meta MMS-TTS (CC-BY-NC 4.0), a self-trained VITS checkpoint via `custom_vits` (OSI-clean path, no ready checkpoint exists yet), and a phrase-splicing pre-recorded-clip fallback (fully functional today, no ML model or license needed). | `TAURA_TTS_BACKEND=mms`, `custom_vits` (+ `TAURA_TTS_CUSTOM_VITS_MODEL_ID`), or `phrase_splicing` (see `data/audio_clips/README.md`) |
| Response generation | `src/taura/response_generator.py` | `TemplateResponseGenerator` (default, real, deterministic) implemented; `LLMResponseGenerator` is a wiring stub | Implement `LLMResponseGenerator._call_model()` against a chosen provider, then set `TAURA_RESPONSE_BACKEND=llm` |

### ASR backend detail

`get_speech_recognizer()` in `src/taura/asr.py` selects between three
backends via `TAURA_ASR_BACKEND`:

- `passthrough` (default) -- no dependencies beyond the standard library;
  used by every simulator, the web demo, and the test suite.
- `mms` -- `MMSSpeechRecognizer` loads `facebook/mms-1b-all` via
  `transformers.Wav2Vec2ForCTC` with a language adapter (`sna` for Shona,
  `nde` for Zimbabwean/North Ndebele), following Meta's documented HF
  integration. Loading is lazy (first `transcribe()` call, not `__init__`),
  so constructing the object is cheap.
- `whisper_finetuned` -- `WhisperFineTunedASR` loads a Whisper checkpoint
  fine-tuned on the consented pilot-site voice corpus from
  `TAURA_ASR_WHISPER_MODEL_PATH`. Base Whisper does not natively cover
  Shona/Ndebele, so this backend is only meaningful once that fine-tune
  exists (Milestone 1 in the written proposal). Whisper itself is
  MIT-licensed.
- `xlsr_finetuned` -- `XLSRSpeechRecognizer` loads a wav2vec2-XLSR checkpoint
  fine-tuned the same way, from `TAURA_ASR_XLSR_MODEL_PATH`. Apache-2.0 base.
  See `docs/OSI_LICENSED_ALTERNATIVES.md` for why both Whisper and XLSR
  fine-tuning paths are offered rather than just one.

Both real backends raise a clear, actionable `RuntimeError` (not a raw
`ImportError` traceback) when the optional `requirements-asr.txt` dependencies
aren't installed, or when `whisper_finetuned` is selected with no model path
configured -- see `tests/test_asr.py`.

Audio decoding/resampling (arbitrary format -> mono float32 @ 16kHz) lives in
`src/taura/asr_audio_utils.py`, imported lazily by the same two backends so
that `numpy`/`soundfile`/`librosa` are never required for the default path
either.

### TTS backend detail

`get_speech_synthesizer()` in `src/taura/tts.py` selects between three
backends via `TAURA_TTS_BACKEND`:

- `passthrough` (default) -- returns text unchanged, no audio; used by every
  simulator, the web demo, and the test suite.
- `mms` -- `MMSTextToSpeech` loads a per-language MMS-TTS checkpoint
  (`facebook/mms-tts-sna`, `facebook/mms-tts-nde`, ...) via
  `transformers.VitsModel` and encodes the output waveform to WAV. Like MMS
  ASR, this is CC-BY-NC 4.0 (non-commercial) -- see
  `docs/ASSET_LICENSE_REGISTER.md`.
- `custom_vits` -- the identical `VitsModel` wiring (reuses the
  `MMSTextToSpeech` class), pointed at `TAURA_TTS_CUSTOM_VITS_MODEL_ID`
  instead of Meta's checkpoint template. This is the OSI-clean path: train
  your own VITS model (MIT-licensed reference architecture) on the pilot
  voice corpus. No ready-made checkpoint exists for this yet -- see
  `docs/OSI_LICENSED_ALTERNATIVES.md`.
- `phrase_splicing` -- `PhraseSplicingTTS` plays back a pre-recorded clip for
  an exact match against one of five fixed, variable-free response templates
  (greeting, consent prompt, human handoff, consent-decline, no-data-found),
  looked up via `data/audio_clips_manifest.json`
  (`scripts/generate_clip_manifest.py` generates/refreshes it). This is the
  "pre-recorded fallback for top intents" mitigation named in the written
  proposal, Section 4.5 -- fully functional today, requires no ML model and
  carries no licensing constraint, but by design does **not** cover price/
  climate/financial responses (they contain variable data no fixed clip can
  represent) -- those fall back to text-only output, not an error. See
  `data/audio_clips/README.md` for the recording process.

All three backends return the same `SynthesizedSpeech` dataclass
(`text`, `language`, `audio_bytes`, `source`) so the orchestrator and every
channel simulator are unaffected by which backend is active.

## The grounding rule (why AI is justified, not decorative)

`RagRetriever.find_price()`, `find_climate_alert()`, and
`find_financial_products()` are the *only* way a price, weather, or
financial-product record reaches the response generator. If retrieval finds
nothing, the response generator returns `no_data_found()` rather than letting
either backend guess. This is enforced in code, not just described in prose:
see `tests/test_orchestrator.py::test_price_query_with_no_matching_data_falls_back`
and `RagRetriever.find_price()`'s explicit `if not entities.commodity: return
None` fail-closed check in `src/taura/rag_retriever.py`.

## Data flow vs. the proposal's grounding-data-sources layer

| Proposal diagram box | Repository equivalent |
|---|---|
| AMA / ZIMSTAT market price bulletins | `data/market_prices.json` (synthetic sample; see `docs/DATASET_STATEMENT.md`) |
| MSD & Dept. of Civil Protection alerts | `data/climate_alerts.json` (synthetic sample) |
| EcoCash / MFI / bank product catalogue | `data/financial_products.json` (synthetic sample) |
| Verified knowledge base | `data/knowledge_base.json` (synthetic sample) |
| Session Store & Audit Log | `logs/audit.log` via `src/taura/audit_log.py` (JSONL; swap for Postgres in production) |
| Admin Console | Not yet implemented in this prototype; `read_all_entries()` in `audit_log.py` is the first building block for one |

## Deployment target

The written proposal (Section 3.3) targets ZCHPC's Cloud Compute
Environment. That environment is a self-managed Xen Orchestra virtual
machine (confirmed against ZCHPC's own HPC Access Guide and User Manual, not
assumed) — a standard Ubuntu VM you administer over SSH, not a Kubernetes
cluster or PaaS. This repository's `Dockerfile` and `docker-compose.yml` are
already the right deployment artifact for that target; `deploy/zchpc/`
adds what a bare VM needs beyond `docker compose up` — a bootstrap script,
a systemd unit, a TLS reverse proxy, and a backup plan. See
[`deploy/zchpc/README.md`](../deploy/zchpc/README.md) for the full runbook.

## Extending to a new language or district

1. Add price/alert/financial records for the new district to the relevant
   JSON file in `data/` (no code change needed if the schema is followed).
2. Add commodity aliases / location names to
   `src/taura/entity_extractor.py`'s `KNOWN_LOCATIONS` list or the price
   data's `commodity_aliases`.
3. Add intent keywords for the new language to
   `src/taura/intent_classifier.py` and marker words to
   `src/taura/language_detector.py`.
4. Add phrase templates for the new language to
   `src/taura/response_generator.py`.

No change to the orchestrator, retriever interfaces, or channel simulators is
required -- this is the replicability property described in Section 5.6 of
the written proposal.
