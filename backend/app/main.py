import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.app.services.search_pipeline import SearchPipeline
from backend.app.services.guardrail import CitationGuardrail
from backend.app.services.citation_oracle import CitationOracle
from backend.app.services.sutta_relations import SuttaRelations
from backend.app.services.sutta_title_index import SuttaTitleIndex
from backend.app.services.bm25_retriever import BM25Retriever

limiter = Limiter(key_func=get_remote_address)

_DUMPS_DIR = Path(__file__).parent.parent.parent / "data" / "dumps"

@asynccontextmanager
async def lifespan(app: FastAPI):
    oracle = CitationOracle(_DUMPS_DIR)
    relations = SuttaRelations(oracle.known_suttas)
    title_index = SuttaTitleIndex.from_directory(_DUMPS_DIR)
    bm25_retriever = BM25Retriever.from_directory(_DUMPS_DIR)
    app.state.pipeline = SearchPipeline(
        sutta_relations=relations,
        title_index=title_index,
        bm25_retriever=bm25_retriever,
    )
    app.state.guardrail = CitationGuardrail(oracle=oracle)
    yield
    if pipeline := getattr(app.state, "pipeline", None):
        pipeline.shutdown()

app = FastAPI(title="Pali Canon AI Search API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_allowed_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/search")
@limiter.limit("30/minute")
async def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500, description="The search query in English or Pali"),
    top_k: int = Query(default=10, ge=1, le=20, description="Number of results to return"),
    nikayas: Optional[List[str]] = Query(default=None, description="Filter by Nikaya (DN, MN, SN, AN, DHP, ITI)"),
):
    pipeline = request.app.state.pipeline
    results = await pipeline.search(q, top_k=top_k, nikayas=nikayas or None)
    related_suttas = pipeline.get_related_suttas(results)
    return {"query": q, "results": results, "related_suttas": related_suttas}

@app.get("/synthesize")
@limiter.limit("10/minute")
async def synthesize(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500, description="The question to answer"),
    top_k: int = Query(default=10, ge=1, le=20, description="Number of context chunks to retrieve"),
):
    # 1. Retrieve relevant context
    context = await request.app.state.pipeline.search(q, top_k=top_k)

    # 2. Synthesize answer
    answer = await request.app.state.pipeline.synthesize(q, context)

    # 3. Verify citations using the guardrail
    verification = request.app.state.guardrail.process_response(answer, context)

    return {
        "query": q,
        "answer": verification["text"],
        "hallucinations": verification["hallucinations"],
        "canonical_misses": verification["canonical_misses"],
        "is_faithful": verification["is_faithful"],
        "context": context
    }

@app.get("/stream")
@limiter.limit("10/minute")
async def stream(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500, description="The question to answer"),
    top_k: int = Query(default=10, ge=1, le=20, description="Number of context chunks to retrieve"),
    nikayas: Optional[List[str]] = Query(default=None, description="Filter by Nikaya (DN, MN, SN, AN, DHP, ITI)"),
):
    async def event_stream():
        yield f"data: {json.dumps({'type': 'status', 'text': 'Searching the Canon…'})}\n\n"
        context = await request.app.state.pipeline.search(q, top_k=top_k, nikayas=nikayas or None)
        yield f"data: {json.dumps({'type': 'status', 'text': 'Composing answer…'})}\n\n"
        async for event in request.app.state.pipeline.stream_synthesize(q, context):
            if event["type"] == "chunk":
                yield f"data: {json.dumps(event)}\n\n"
            else:
                verification = request.app.state.guardrail.process_response(event["text"], context)
                yield f"data: {json.dumps({'type': 'done', 'query': q, 'answer': verification['text'], 'hallucinations': verification['hallucinations'], 'canonical_misses': verification['canonical_misses'], 'is_faithful': verification['is_faithful'], 'context': context})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
