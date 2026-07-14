# Audio clips for PhraseSplicingTTS

This directory holds pre-recorded audio clips for the **fixed, variable-free**
response templates -- the "pre-recorded fallback for top intents" mitigation
named in the written proposal (Section 4.5, TTS quality risk). No clips are
bundled in this repository yet: this is the process for recording and adding
them, not the recordings themselves.

## Why only some responses can be covered this way

`PhraseSplicingTTS` (see `src/taura/tts.py`) works by exact text match: it
plays back a recorded clip only when the response text is *identical* to one
it has a recording for. That's true for:

- Greeting (`KB-GREETING-001`)
- Consent prompt (`KB-CONSENT-001`)
- Human handoff (`KB-HANDOFF-001`)
- Consent-decline acknowledgement (`CONSENT-DECLINE-001`)
- No-data-found fallback (`NO-DATA-FOUND-001`)

It is **not** true for price, climate, or financial responses -- those
contain variable data (a dollar figure, a location name, a week number), so
no fixed clip can represent them. Covering those needs either a real TTS
backend (`TAURA_TTS_BACKEND=mms`, see `src/taura/tts.py`) or a future
extension that concatenates word/number-level clips (a documented next step,
not implemented here -- see "Extending beyond fixed templates" below).

## Recording process

1. **Consent first.** Anyone recording a voice for this must give explicit,
   specific consent for their voice to be used in this product -- separate
   from any product-use consent a farmer/trader gives as an end user. Record
   and retain that consent per `docs/DATASET_STATEMENT.md`.
2. **Generate the current list of what to record:**
   ```bash
   PYTHONPATH=src python scripts/generate_clip_manifest.py
   ```
   This writes/updates `data/audio_clips_manifest.json` with every fixed
   template string, in all three languages, and marks each `"missing"` until
   a file exists at its expected path.
3. **Record each clip** at the path the manifest lists (e.g.
   `data/audio_clips/sn/KB-GREETING-001.wav`), reading the exact `text` shown
   in the manifest entry for that language.
   - Format: mono WAV, 16-bit PCM, 16kHz or 22.05kHz (consistent with
     whatever the eventual playback channel expects -- confirm against your
     telephony/WhatsApp gateway's requirements before finalising).
   - Keep a consistent voice/tone across all clips in a language -- a farmer
     calling twice should hear the same "Taura voice" both times.
4. **Re-run the generator script** to flip newly-recorded entries from
   `"missing"` to `"recorded"` in the manifest.
5. **Set `TAURA_TTS_BACKEND=phrase_splicing`** and test via the CLI or web
   demo -- greetings and handoffs should now play back real audio; price/
   climate queries will still return text-only (`audio_bytes=None`), which is
   expected (see above).

## Extending beyond fixed templates (not implemented here)

To cover price/climate/financial responses without a full neural TTS model,
the next step would be a word/number clip library (digits 0-9, common
commodity names, common location names, units) concatenated at inference
time to match the response template's slots. This is meaningfully more work
than fixed-template splicing (audio splicing artefacts at clip boundaries
need smoothing, numbers need correct grammatical agreement in Shona/Ndebele,
etc.) and is out of scope for this prototype -- track it as a possible
Milestone 2 item if `TAURA_TTS_BACKEND=mms` proves too costly or too NC-
license-constrained for production (see `docs/ASSET_LICENSE_REGISTER.md`).
