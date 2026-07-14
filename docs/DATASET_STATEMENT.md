# Dataset Statement

This document accompanies the Taura AI submission for the AI4I 2026 Challenge
(Track 3: Development) and records the provenance, consent status, and
intended use of every data source referenced by the prototype, per the
Track 1 Data Terms of Reference and the Supporting Guidance on Product
Readiness.

## Summary table

| Data | Status | Consent basis | Notes |
|---|---|---|---|
| `data/market_prices.json` | **Synthetic sample** | N/A (no real individuals) | Illustrative commodity price records modelled on the structure of an AMA/ZIMSTAT weekly bulletin. Figures are invented for demo purposes and must not be used as real market information. |
| `data/climate_alerts.json` | **Synthetic sample** | N/A | Illustrative flood/drought/seasonal-outlook records modelled on the structure of an MSD/Civil Protection advisory. Not real forecasts. |
| `data/financial_products.json` | **Synthetic sample** | N/A | Illustrative savings/loan/insurance product summaries. Not real EcoCash or MFI offers; no real institution is named as the provider. |
| `data/knowledge_base.json` | **Synthetic sample** | N/A | Illustrative greeting, consent-prompt and human-handoff copy in Shona/Ndebele/English, written for this prototype. |
| Shona/Ndebele ASR adaptation audio | **Not yet collected** | Explicit, specific consent required before collection | Planned for the post-selection milestone period (see written proposal, Section 3.1). No audio is bundled with this repository. |
| Phrase-splicing TTS clips (`data/audio_clips/`) | **Not yet recorded** | Explicit, specific consent required from voice talent before recording | Only 15 fixed-template strings need recording (5 templates × 3 languages) — see `data/audio_clips/README.md` for the process. No recordings are bundled; `data/audio_clips_manifest.json` currently lists all 15 as `"status": "missing"`. |
| End-user session/consent/audit data | **Not collected by this repository** | N/A | The bundled prototype runs entirely offline against synthetic data; no real end-user data is processed, stored, or transmitted by this codebase as submitted. |

## Why every JSON file is marked "synthetic sample"

Every record in `data/` carries a `_source_note` field stating this
explicitly, and every file's schema is designed to match what a real
institutional feed (AMA/ZIMSTAT, MSD/Civil Protection, EcoCash/MFI) would
provide, so that swapping synthetic files for a live feed at Milestone 1 is a
data-layer change only -- no change to `rag_retriever.py`, the orchestrator,
or the response generator.

## Consent handling implemented in the prototype

Although no real user data is collected by this repository, the orchestrator
(`src/taura/orchestrator.py`) implements and unit-tests a consent gate
(`src/taura/consent.py`) that:

1. Blocks any substantive answer until the session records an explicit
   `hongu` / `yebo` / `yes` (or equivalent decline) reply to a consent prompt.
2. Logs the resulting consent status on every audit entry
   (`src/taura/audit_log.py`), never the raw content of a declined session.

This is the mechanism referenced in Section 4.1 of the written proposal and is
exercised directly in `tests/test_orchestrator.py`.

## Planned real data partnerships (not yet executed)

| Source | Owning institution | Status at time of submission |
|---|---|---|
| Weekly commodity price bulletin | Agricultural Marketing Authority (AMA) / ZIMSTAT | Partnership request to be initiated during the Challenge support window |
| Rainfall/flood/drought advisories | Meteorological Services Department (MSD) / Department of Civil Protection | Partnership request to be initiated during the Challenge support window |
| Mobile money / MFI product catalogue | To be confirmed with a participating EcoCash-integrated MFI | Requires a signed data-sharing agreement before any real product content is served |

## Data minimisation and retention (design commitment)

- Raw audio is not retained beyond ASR processing unless a user has given
  separate, specific consent for voice-data collection (see written proposal,
  Section 4.1).
- Session logs store only the fields needed for service delivery and audit:
  detected intent, retrieved source record id, response text, and outcome
  flag -- not free-form personal data beyond what the user volunteers in their
  query.
- No data in this repository, synthetic or otherwise, is used for any purpose
  beyond demonstrating and testing the Taura AI product logic.
