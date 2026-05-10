import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.app.services.search_pipeline import SearchPipeline
from backend.app.services.guardrail import CitationGuardrail

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pipeline = SearchPipeline()
    app.state.guardrail = CitationGuardrail()
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
):
    results = await request.app.state.pipeline.search(q, top_k=top_k)
    return {"query": q, "results": results}

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
        "is_faithful": verification["is_faithful"],
        "context": context
    }

@app.get("/stream")
@limiter.limit("10/minute")
async def stream(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500, description="The question to answer"),
    top_k: int = Query(default=10, ge=1, le=20, description="Number of context chunks to retrieve"),
):
    async def event_stream():
        context = await request.app.state.pipeline.search(q, top_k=top_k)
        async for event in request.app.state.pipeline.stream_synthesize(q, context):
            if event["type"] == "chunk":
                yield f"data: {json.dumps(event)}\n\n"
            else:
                verification = request.app.state.guardrail.process_response(event["text"], context)
                yield f"data: {json.dumps({'type': 'done', 'query': q, 'answer': verification['text'], 'hallucinations': verification['hallucinations'], 'is_faithful': verification['is_faithful'], 'context': context})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
