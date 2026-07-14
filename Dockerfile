# Taura AI reference prototype - backend + web demo container.
# Builds a lightweight image sufficient for the offline template-response
# demo. Swapping TAURA_RESPONSE_BACKEND=llm and integrating real ASR/TTS
# models is expected to require a larger, GPU-enabled base image; see
# src/taura/asr.py, src/taura/tts.py and src/taura/response_generator.py for
# the integration points.

FROM python:3.11-slim

WORKDIR /app

# System deps kept minimal; add build tools here only if a real ASR/TTS/LLM
# dependency you integrate later needs them.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \
    TAURA_DATA_DIR=/app/data \
    TAURA_LOG_DIR=/app/logs

RUN mkdir -p /app/logs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
