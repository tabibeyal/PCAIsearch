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
    rank-bm25==0.2.2

COPY backend/ backend/
COPY data/dumps/ data/dumps/

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
