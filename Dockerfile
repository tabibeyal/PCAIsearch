FROM python:3.11-slim

WORKDIR /app

# CPU-only torch first — avoids downloading 2GB CUDA build
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir \
    fastapi==0.136.1 \
    uvicorn==0.46.0 \
    openai==2.33.0 \
    qdrant-client==1.17.1 \
    sentence-transformers==5.4.1 \
    fastembed==0.8.0 \
    slowapi==0.1.9 \
    rank-bm25==0.2.2 \
    resend==2.10.0

RUN useradd -m appuser

# Explicit cache paths so build-time downloads land in the same place
# the app reads at runtime (avoids $HOME ambiguity on App Platform).
ENV FASTEMBED_CACHE_PATH=/app/model_cache
ENV SENTENCE_TRANSFORMERS_HOME=/app/model_cache

COPY --chown=appuser:appuser backend/ backend/
COPY --chown=appuser:appuser data/dumps/ data/dumps/

RUN mkdir -p /app/model_cache && chown appuser:appuser /app/model_cache

USER appuser

# Pre-download both ML models at build time so startup is instant.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')" && \
    python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')" && \
    echo "model cache:" && ls /app/model_cache/

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
