# Evaluating OSI-Licensed Alternatives to MMS

`docs/ASSET_LICENSE_REGISTER.md` flags that Meta's MMS checkpoints — both
`facebook/mms-1b-all` (ASR) and `facebook/mms-tts-<lang>` (TTS) — are
CC-BY-NC 4.0, non-commercial only. That's a real constraint on the paid-pilot
sustainability model in the written proposal (Section 5). This document
evaluates what a genuinely OSI-licensed (commercial-safe) path looks like for
each, based on checking actual license terms and language coverage rather
than assuming a permissively-licensed model automatically covers Shona and
Ndebele — most don't, out of the box.

## Bottom line

**There is no ready-to-download, commercial-safe, Shona/Ndebele-capable ASR
or TTS checkpoint today.** Every permissively-licensed model evaluated below
is either (a) commercial-safe but requires fine-tuning on a Shona/Ndebele
corpus before it's usable, or (b) ready-to-use but doesn't cover these
languages. The practical recommendation is: **use an Apache-2.0/MIT base
model and fine-tune it on the pilot-site voice corpus**, rather than waiting
for or hoping to find a pre-built alternative. This is more work than
downloading MMS, but it removes the licensing constraint entirely and the
team ends up owning a checkpoint trained on its own target dialect/domain
vocabulary (agricultural and financial terms) either way.

## ASR options evaluated

| Option | License | Confirmed | Shona/Ndebele coverage | Verdict |
|---|---|---|---|---|
| `facebook/mms-1b-all` (current default) | CC-BY-NC 4.0 | Yes, via model card + fairseq release notes | Yes, out of the box (`sna`, `nde` adapters) | Ready to use, **not commercial-safe** |
| OpenAI Whisper (all sizes, incl. `large-v3`) | **MIT** | Yes, via the `openai/whisper` repo's `LICENSE` file | **No** — not in Whisper's ~99 supported languages | Commercial-safe, but unusable for Shona/Ndebele without fine-tuning |
| `facebook/wav2vec2-large-xlsr-53` (the original XLSR, distinct from MMS) | **Apache-2.0** | Yes, via the Hugging Face model card | **No** ready checkpoint for Shona/Ndebele, but the multilingual pretrained backbone is designed to be fine-tuned per-language on a few hours of labelled speech (this is exactly how the ~100 community XLSR fine-tunes for other languages, e.g. Russian, French, were made) | Commercial-safe, fine-tune-your-own — **recommended primary path**, now wired (see below) |
| Mozilla Common Voice (as a training corpus, not a model) | CC0 (public domain) | Yes, per Mozilla's dataset release notes | **Unconfirmed for Shona; "IsiNdebele" was added in Common Voice 20 (Dec 2024), but that is Southern Ndebele (South Africa, ISO 639-3 `nbl`) — not Zimbabwean/Northern Ndebele (`nde`).** Do not assume this covers the target language without checking `commonvoice.mozilla.org/en/languages` directly for the current release. | Useful as a training-data source only if/when Shona or `nde`-specific Ndebele is added; not a substitute for the pilot-site corpus either way, since neither would cover agricultural/financial vocabulary |
| NVIDIA NeMo (Canary/Parakeet models) | CC-BY-4.0 (commercial-safe, attribution required) | Per NVIDIA's model cards | No Shona/Ndebele checkpoints found | Not evaluated further — same fine-tune-your-own story as XLSR, with a heavier toolkit and no clear advantage for this use case |

### Why `wav2vec2-large-xlsr-53` over fine-tuning Whisper

Both are legitimate commercial-safe fine-tuning bases and the repo already
supports Whisper fine-tuning (`WhisperFineTunedASR`). XLSR-53 is added as a
second option because:

- It's a CTC (connectionist temporal classification) architecture, generally
  reported to need **less labelled data** to reach usable accuracy on a new
  low-resource language than fine-tuning Whisper's full sequence-to-sequence
  decoder — relevant given the pilot-site corpus will start small.
- It's smaller (315M parameters vs. Whisper large's 1.5B), so CPU inference
  and fine-tuning are cheaper — relevant given the open GPU-availability
  question already flagged in `deploy/zchpc/VM_SIZING.md`.
- Having two viable, license-clean fine-tuning paths is itself useful: if one
  approach underperforms on Shona/Ndebele's tonal and agglutinative
  characteristics during the Milestone 1 benchmark, the team isn't blocked
  waiting on a single architecture to work.

This is a judgement call based on general low-resource ASR fine-tuning
patterns, not a claim backed by a Shona/Ndebele-specific benchmark — no such
benchmark exists yet. Milestone 1's ASR benchmark (written proposal, Section
3.1) should test both and report which performs better, rather than
committing to one now.

## TTS options evaluated

| Option | License | Confirmed | Shona/Ndebele coverage | Verdict |
|---|---|---|---|---|
| `facebook/mms-tts-<lang>` (current default) | CC-BY-NC 4.0 | Yes, same MMS release family as the ASR checkpoint | Yes, out of the box (`mms-tts-sna`, likely `mms-tts-nde` — confirm exact checkpoint id exists before relying on it) | Ready to use, **not commercial-safe** |
| Coqui TTS toolkit (the Python library/training code) | **MPL 2.0** (commercial-safe, must disclose modifications to the toolkit itself) | Yes, via the `coqui-ai/TTS` repo (now community-maintained as `idiap/coqui-ai-TTS` / PyPI `coqui-tts` after Coqui Inc. shut down in Jan 2024) | N/A — this is a toolkit, not a voice | The toolkit license is clean, but... |
| Coqui TTS's bundled "Fairseq VITS" models (`tts_models/<iso>/fairseq/vits`, ~1100 languages incl. likely Shona/Ndebele) | **CC-BY-NC 4.0** | These are the *same underlying Meta MMS-TTS checkpoints*, loaded through Coqui's convenience wrapper — confirmed by Coqui's own docs pointing to the fairseq/MMS project | Yes, inherited from MMS | **Not a real alternative** — same NC restriction as using MMS-TTS directly through `transformers`, just via a different library. This is an easy trap: "open-source toolkit" does not mean "open-source weights". |
| XTTS v2 (Coqui's flagship voice-cloning model) | Coqui Public Model License (CPML) — **non-commercial** | Yes | 17 languages, none are Shona/Ndebele | Not usable either way |
| Piper (lightweight, embedded-focused TTS) | **MIT** (both code and released voices) | Yes | No Shona/Ndebele voice found in Piper's voice list | Commercial-safe, but no ready voice — would need training a new Piper voice from scratch |
| Original VITS reference implementation (Kim et al., the architecture MMS-TTS and Piper both build on) | **MIT** | Yes (`jaywalnut310/vits` on GitHub) | N/A — architecture only, no pretrained weights released for any language by the original authors | The clean-room path: train your own VITS model on your own consented Shona/Ndebele recordings, using either the original repo, Piper's training pipeline, or the Coqui MPL 2.0 toolkit purely as *training code* (not their NC-licensed pretrained checkpoints) |

### The practical TTS recommendation

Given no commercial-safe, ready-made Shona/Ndebele voice exists anywhere
evaluated, there are two real options, both already reflected in this
repository:

1. **`TAURA_TTS_BACKEND=phrase_splicing`** (already implemented, see
   `src/taura/tts.py` and `data/audio_clips/README.md`) — zero licensing risk,
   zero training cost, but only covers the 5 fixed response templates.
2. **Train your own VITS model** on the same consented pilot-site voice
   corpus planned for ASR fine-tuning (see `docs/DATASET_STATEMENT.md`),
   using MIT/MPL-licensed training code. The resulting checkpoint is fully
   team-owned with no NC restriction. `MMSTextToSpeech` in `src/taura/tts.py`
   already loads *any* `transformers`-compatible VITS checkpoint via
   `TAURA_TTS_MMS_MODEL_ID_TEMPLATE` — pointing that at a self-trained,
   privately-hosted checkpoint instead of `facebook/mms-tts-{lang}` reuses
   the exact same wiring with no code change. See the `custom_vits` backend
   added below for a version of this that doesn't require overloading the
   "mms" name.

## What changed in the code as a result of this evaluation

- **`XLSRSpeechRecognizer`** added to `src/taura/asr.py` — real wiring for
  `wav2vec2-large-xlsr-53`-family fine-tuned checkpoints (Apache-2.0 base),
  selected via `TAURA_ASR_BACKEND=xlsr_finetuned` +
  `TAURA_ASR_XLSR_MODEL_PATH`. Mirrors `WhisperFineTunedASR`'s pattern: no
  ready-made checkpoint is assumed, the class requires a fine-tuned model
  path and fails with a clear, actionable error if one isn't configured.
- **`custom_vits` TTS backend** added to `src/taura/tts.py` — the same
  `MMSTextToSpeech`/`VitsModel` wiring, explicitly renamed at the config
  level so choosing it doesn't imply using Meta's NC checkpoint. Selected via
  `TAURA_TTS_BACKEND=custom_vits` + `TAURA_TTS_CUSTOM_VITS_MODEL_ID`.
- This evaluation document and updated entries in
  `docs/ASSET_LICENSE_REGISTER.md`.

Neither new code path has been run against a real checkpoint in this
environment (no network access to the Hugging Face Hub, and no fine-tuned
Shona/Ndebele checkpoint exists yet for either architecture) — same
verification status as the existing MMS and Whisper wiring, and the same
Milestone 1 benchmark work item.
