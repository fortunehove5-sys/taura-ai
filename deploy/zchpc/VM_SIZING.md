# VM Sizing — ZCHPC HPC Cloud

Recommended VM specifications for each deployment stage, to request when
creating the VM in Xen Orchestra (`https://cloud.zchpc.ac.zw`) or when
discussing an allocation with ZCHPC support.

## Stage 1 — Pilot demo (current default: `TAURA_ASR_BACKEND=passthrough`, `TAURA_RESPONSE_BACKEND=template`)

| Resource | Recommendation | Why |
|---|---|---|
| vCPU | 2 | FastAPI + template response generation is not compute-heavy |
| RAM | 4 GB | Matches the limit set in `docker-compose.zchpc.yml` |
| Disk | 20 GB | OS + Docker images + logs; the JSON sample data is a few KB |
| GPU | None needed | No ASR/TTS/LLM inference running at this stage |
| Network | Public IP + a domain pointed at it (for Caddy's automatic HTTPS) | See `deploy/zchpc/Caddyfile` |

This is enough to run the full offline demo (web UI, all three channel
simulators via SSH, the FastAPI backend) for bootcamp/judge access, and
matches what's actually implemented and tested today.

## Stage 2 — Milestone 1 ASR benchmark (`TAURA_ASR_BACKEND=mms` or `whisper_finetuned`)

| Resource | Recommendation | Why |
|---|---|---|
| vCPU | 4–8 | `transformers`/`torch` model loading and CPU inference, if no GPU is granted |
| RAM | 16 GB | MMS (`facebook/mms-1b-all`) is a ~1B-parameter model; needs headroom beyond the base weights for batching |
| Disk | 40–60 GB | Model checkpoint cache (`~/.cache/huggingface`), audio corpus samples |
| GPU | Requested but not guaranteed — see below | Real-time inference target (written proposal, Section 3.2: <4s end-to-end) is unlikely on CPU alone at pilot call volumes |

**GPU availability is an open item, not a confirmed allocation.** ZCHPC's
publicly documented HPC Cloud account tier (Xen Orchestra VM self-service) is
CPU/RAM/disk only in the standard user manual; the HPC Data Centre itself has
GPU servers, but VM-level GPU passthrough for a specific project needs to be
requested and confirmed directly with ZCHPC (`business@zchpc.ac.zw`,
+263 719 479 129) before this is assumed in a budget or timeline. If GPU
passthrough isn't available at this tier, the fallback is CPU inference with
a relaxed latency target for the benchmark, or a commercial GPU cloud
provider for this milestone specifically — track this as a Milestone 1 risk
alongside the ASR licensing question in `docs/ASSET_LICENSE_REGISTER.md`.

## Stage 3 — Pilot (Section 3.1 Milestone 2 in the written proposal, ~200 active users)

| Resource | Recommendation | Why |
|---|---|---|
| vCPU | 8 | Concurrent sessions across voice/USSD/WhatsApp |
| RAM | 16–32 GB | Model(s) resident in memory + concurrent request handling |
| Disk | 80–100 GB | Growing audit log, session data once moved off JSONL to Postgres (see `docs/ARCHITECTURE.md`) |
| GPU | Same open item as Stage 2 | |

These figures are planning estimates, not a confirmed ZCHPC quotation —
validate against real allocation limits and, if applicable, ZCHPC's pricing
for the HPC Cloud tier before finalising the Milestone budget referenced in
the written proposal (Section 5.2).
