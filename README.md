# Taura AI
![Taura AI CI](https://github.com/fortunehove5-sys/taura-ai/actions/workflows/ci.yml/badge.svg)
**A voice-first AI advisory agent for financial inclusion and climate resilience in Zimbabwe's informal economy.**

*"Taura" — Shona for "speak."*

Submitted for the **2026 AI For Impact (AI4I) Challenge — Track 3: Development**.
See the full written proposal: `Taura_AI_Proposal.pdf` (in the parent
submission package) for problem definition, strategic alignment, roadmap,
compliance/risk analysis, and sustainability plan.

This repository is the working reference prototype for that proposal. It
demonstrates the product logic end-to-end — consent handling, multilingual
(Shona / Ndebele / English) intent understanding, retrieval-grounded
responses, and a human-escalation path — over three simulated channels
(voice call, USSD, WhatsApp) plus a browser-based demo, all running fully
offline against **synthetic sample data**.

> **What this is / is not:** This is an architecture and product-logic
> prototype, not a production deployment. Real ASR wiring for Meta MMS and a
> fine-tuned Whisper checkpoint is implemented in `src/taura/asr.py` (see
> below), but has not been run against real audio in this environment — no
> network access to the Hugging Face Hub, no GPU. Text-to-speech and live
> institutional data feeds remain stubbed integration points, clearly marked
> — see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for exactly what to
> swap in and where. No real user data, and no real AMA/MSD/EcoCash data, is
> used anywhere in this repository — see
> [`docs/DATASET_STATEMENT.md`](docs/DATASET_STATEMENT.md).

---

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q                        # 57 tests, all offline, ~0.4s
```

### Run the web demo (recommended for a first look)

```bash
uvicorn backend.app:app --reload --port 8000
```

Then open **http://localhost:8000** — a WhatsApp-style chat window on the
left, and a "grounding inspector" panel on the right showing the detected
language, classified intent, escalation status, and (in the chat itself)
which verified source record each answer was grounded in.

### Run the channel simulators

```bash
# Voice-call-style free-text chat in the terminal
python -m taura.channels.cli_chat

# Scripted WhatsApp exchange (no input needed, just run it)
python -m taura.channels.whatsapp_simulator

# Menu-driven USSD session
python -m taura.channels.ussd_simulator
```

(Run these with `PYTHONPATH=src` set, or via `./scripts/run_cli_demo.sh` for
the CLI one, which sets it up for you.)

### Run with Docker

```bash
docker compose up --build
```

Then open **http://localhost:8000**.

### Deploying to ZCHPC's HPC Cloud

The written proposal targets ZCHPC's Cloud Compute Environment for the pilot.
That environment is a self-managed Xen Orchestra VM (not Kubernetes) — see
[`deploy/zchpc/README.md`](deploy/zchpc/README.md) for the full, grounded
runbook (VM provisioning, systemd service, TLS reverse proxy, backups), based
on ZCHPC's own published HPC Access Guide and User Manual.

### Using real ASR/TTS backends (optional)

By default the app runs `TAURA_ASR_BACKEND=passthrough` and
`TAURA_TTS_BACKEND=passthrough` (no audio model, text in/out). Real wiring
for both is implemented:

```bash
pip install -r requirements-asr.txt   # heavy optional deps: torch, transformers, scipy, etc.

# ASR -- Meta MMS (facebook/mms-1b-all), Shona ("sna") or Ndebele ("nde") adapter
export TAURA_ASR_BACKEND=mms
export TAURA_ASR_MMS_LANGUAGE=sna     # or "nde"

# -- OR -- a Whisper checkpoint fine-tuned on the pilot-site voice corpus
export TAURA_ASR_BACKEND=whisper_finetuned
export TAURA_ASR_WHISPER_MODEL_PATH=/path/to/finetuned-checkpoint

# TTS -- Meta MMS-TTS (facebook/mms-tts-<lang>), one checkpoint per language
export TAURA_TTS_BACKEND=mms

# -- OR -- pre-recorded clips for the 5 fixed response templates (no ML model,
# no licensing constraint -- see data/audio_clips/README.md to record them)
export TAURA_TTS_BACKEND=phrase_splicing
```

All four real backends require network access to download the base
checkpoint on first use (or a local fine-tuned checkpoint / recorded clips
for the non-MMS paths) and are not exercised end-to-end in this submission
environment — see `docs/ARCHITECTURE.md` → "ASR backend detail" / "TTS
backend detail" for what is and isn't verified.

**Licensing note:** Meta's MMS checkpoints (both ASR and TTS) are CC-BY-NC
4.0 — non-commercial use only. This is a real constraint on the paid-pilot
sustainability model in the written proposal; see
`docs/ASSET_LICENSE_REGISTER.md` before any paid deployment. See
`docs/OSI_LICENSED_ALTERNATIVES.md` for a full evaluation of commercial-safe
alternatives (short version: fine-tune Whisper or wav2vec2-XLSR for ASR;
train your own VITS checkpoint for TTS — no ready-made commercial-safe
Shona/Ndebele model exists for either today).

---

## What it does

Taura AI answers three kinds of question, in Shona, Ndebele, or English,
over voice/USSD/WhatsApp:

1. **Crop and livestock prices** — e.g. *"mutengo wechibage muMutare"* (maize
   price in Mutare) — grounded in a (synthetic, sample) AMA/ZIMSTAT-style
   price bulletin.
2. **Climate and flood/drought alerts** — e.g. *"isikhukhula eChipinge"*
   (flood alert for Chipinge) — grounded in a (synthetic, sample)
   MSD/Civil-Protection-style advisory.
3. **Financial literacy and product signposting** — savings, loans,
   insurance — grounded in a (synthetic, sample) product catalogue, with
   loan/insurance queries automatically flagged for **human escalation**,
   since the AI never completes a financial transaction on its own.

Every substantive answer is traced to a specific retrieved source record —
never freely generated — and every turn is written to a structured audit log
(`logs/audit.log`) after explicit user consent.

## Try it: example queries

| Language | Example | Expect |
|---|---|---|
| Shona | `Mhoro` | Consent prompt, then greeting |
| Shona | `mutengo wechibage muMutare` | Maize price in Mutare, grounded |
| Ndebele | `inani lomumbila eBulawayo` | Maize price in Bulawayo, grounded |
| Shona | `kuzonaya here muGokwe` | Dry-spell watch advisory for Gokwe |
| Ndebele | `isikhukhula eChipinge` | Flood warning for Chipinge |
| English | `I want a loan` | Loan product info + escalated to human agent |
| Any | `ndinoda kutaura nemunhu` | Immediate human handoff |

## Repository layout

```
taura-ai/
├── README.md                     you are here
├── LICENSE                       MIT
├── .env.example                  all configurable settings, no secrets required
├── docker-compose.yml / Dockerfile
├── requirements.txt              direct dependencies
├── requirements.lock.txt         pinned, reproducible dependency versions
├── requirements-asr.txt          optional heavy deps for real ASR (torch, transformers, ...)
├── pytest.ini
├── data/                         synthetic sample "grounding" data sources
│   ├── market_prices.json
│   ├── climate_alerts.json
│   ├── financial_products.json
│   ├── knowledge_base.json
│   ├── audio_clips/              phrase-splicing TTS clips (none recorded yet, see README.md inside)
│   └── audio_clips_manifest.json generated by scripts/generate_clip_manifest.py
├── src/taura/                    core package
│   ├── config.py
│   ├── consent.py
│   ├── audit_log.py
│   ├── language_detector.py
│   ├── intent_classifier.py
│   ├── entity_extractor.py
│   ├── rag_retriever.py
│   ├── response_generator.py
│   ├── asr.py                    ASR: passthrough (default) + real MMS/Whisper wiring
│   ├── asr_audio_utils.py        audio decode/resample helpers (lazy-imported)
│   ├── tts.py                    TTS: passthrough (default) + real MMS + phrase-splicing wiring
│   ├── orchestrator.py           ties the whole pipeline together
│   └── channels/
│       ├── cli_chat.py
│       ├── whatsapp_simulator.py
│       └── ussd_simulator.py
├── backend/app.py                FastAPI server (chat API + serves webapp/)
├── webapp/                       browser chat UI + grounding inspector
├── tests/                        57 pytest unit/integration tests
├── scripts/
│   ├── run_cli_demo.sh
│   └── generate_clip_manifest.py
├── deploy/zchpc/                 real deployment runbook for ZCHPC's Xen Orchestra HPC Cloud
│   ├── README.md                 step-by-step VM provisioning + deployment
│   ├── cloud-init.yaml           VM bootstrap (Docker, firewall, service account)
│   ├── taura-backend.service     systemd unit (survives reboot/failure)
│   ├── docker-compose.zchpc.yml  prod overrides: resource limits, Caddy TLS proxy
│   ├── Caddyfile                 reverse proxy config
│   ├── VM_SIZING.md              vCPU/RAM/disk per stage + the GPU open item
│   └── backup.sh                 audit log backup, cron-able
└── docs/
    ├── ARCHITECTURE.md           proposal diagram <-> code mapping
    ├── DATASET_STATEMENT.md      data provenance & consent
    ├── DEMO_SCRIPT.md            suggested bootcamp/judge walkthrough
    ├── ASSET_LICENSE_REGISTER.md
    └── OSI_LICENSED_ALTERNATIVES.md   evaluation of commercial-safe ASR/TTS alternatives to MMS
```

## Design principles (see `docs/ARCHITECTURE.md` for detail)

- **Grounding over generation.** Prices, weather, and financial-product facts
  are never freely generated — they are retrieved from a verified source
  record first, and the language layer's only job is to phrase that record
  naturally. If nothing is retrieved, the system says so rather than
  guessing.
- **Same backend, every channel.** Voice, USSD, and WhatsApp all call
  `Orchestrator.handle_turn()` — the AI logic is identical across channels;
  only the transport differs.
- **Consent before content.** No substantive answer is given until a session
  has explicit, logged consent.
- **Human escalation is a first-class outcome**, not an error path — any
  financial product requiring sign-off is automatically flagged.
- **Every stub is a named, documented integration point** (`asr.py`,
  `tts.py`, `LLMResponseGenerator`), not a silent gap.

## Testing

```bash
pytest -q
```

57 tests cover: multilingual intent classification (incl. Shona
agglutination handling), entity extraction, RAG retrieval (incl. fail-closed
behaviour when nothing matches), template response generation in three
languages, ASR/TTS backend selection and error handling across all four
ASR backends and four TTS backends (incl. phrase-splicing fallback
behaviour), and full end-to-end orchestration flows (consent, escalation,
each intent type) across simulated sessions.

## Relationship to the written proposal

This repository implements the architecture described in Section 2 of the
written proposal and the roadmap in Section 3. It is the "working,
demonstrable AI product" deliverable referenced there; it is not the full
production system described in Sections 3–5 (real ASR/TTS, live data
partnerships, ZCHPC HPC Cloud deployment, and a paying institutional
partner), which are the Milestone 1–3 deliverables if the submission is
selected. See [`deploy/zchpc/README.md`](deploy/zchpc/README.md) for the
concrete deployment runbook once that's ready to happen.
