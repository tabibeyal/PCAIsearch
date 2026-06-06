import asyncio
import json
import logging
import os
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal, Optional

import httpx
from pydantic import BaseModel, Field
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse
from backend.app.services.search_pipeline import SearchPipeline
from backend.app.services.guardrail import CitationGuardrail
from backend.app.services.citation_oracle import CitationOracle
from backend.app.services.sutta_relations import SuttaRelations
from backend.app.services.sutta_title_index import SuttaTitleIndex
from backend.app.services.bm25_retriever import BM25Retriever

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

_VALID_NIKAYAS = {"DN", "MN", "SN", "AN", "DHP", "ITI"}
_DUMPS_DIR = Path(__file__).parent.parent.parent / "data" / "dumps"
_FEEDBACK_DB = Path(__file__).parent.parent.parent / "feedback.db"
_raw_supabase_url = os.environ.get("SUPABASE_URL") or ""
_SUPABASE_URL = _raw_supabase_url.split("/rest/")[0].rstrip("/") or None
_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")


class FeedbackBody(BaseModel):
    query: str = Field(max_length=600)
    answer: str = Field(max_length=20000)
    rating: Literal["up", "down"]
    category: Optional[Literal[
        "Doctrinally inaccurate",
        "Missing important nuance",
        "Not relevant to my question",
        "Sources don't support the answer",
        "Too vague",
    ]] = None
    comment: Optional[str] = Field(default=None, max_length=2000)


def _init_feedback_db() -> None:
    con = sqlite3.connect(_FEEDBACK_DB)
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                query      TEXT NOT NULL,
                answer     TEXT NOT NULL,
                rating     TEXT NOT NULL,
                category   TEXT,
                comment    TEXT,
                created_at TEXT NOT NULL
            )
        """)
        con.commit()
    finally:
        con.close()


def _insert_feedback(query: str, answer: str, rating: str, category: Optional[str], comment: Optional[str]) -> None:
    con = sqlite3.connect(_FEEDBACK_DB)
    try:
        con.execute(
            "INSERT INTO feedback (query, answer, rating, category, comment, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (query, answer, rating, category, comment, datetime.now(timezone.utc).isoformat()),
        )
        con.commit()
    finally:
        con.close()


async def _insert_feedback_supabase(
    query: str, answer: str, rating: str, category: Optional[str], comment: Optional[str]
) -> None:
    # NOTE: created_at is filled by the DB default (now()), so it is omitted here.
    headers = {
        "apikey": _SUPABASE_KEY,
        "Authorization": f"Bearer {_SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    payload = {"query": query, "answer": answer, "rating": rating, "category": category, "comment": comment}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{_SUPABASE_URL}/rest/v1/feedback", headers=headers, json=payload)
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Supabase feedback insert failed: %s — response body: %s",
            exc,
            exc.response.text,
        )
        raise
    except httpx.HTTPError as exc:
        logger.error("Supabase feedback insert failed (network): %s", exc)
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not (_SUPABASE_URL and _SUPABASE_KEY):
        _init_feedback_db()
    oracle = CitationOracle(_DUMPS_DIR)
    relations = SuttaRelations(oracle.known_suttas)
    title_index = SuttaTitleIndex.from_directory(_DUMPS_DIR)
    bm25_retriever = BM25Retriever.from_directory(_DUMPS_DIR)
    pipeline = SearchPipeline(
        sutta_relations=relations,
        title_index=title_index,
        bm25_retriever=bm25_retriever,
    )
    try:
        await pipeline.retriever.client.create_payload_index(
            collection_name=pipeline.collection_name,
            field_name="nikaya",
            field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
        )
    except UnexpectedResponse as e:
        # Qdrant Cloud free tier returns 403 for index management operations.
        # The app works without this index — nikaya filtering just uses a scan.
        logger.warning("Could not create nikaya payload index (skipping): %s", e)
    app.state.pipeline = pipeline
    app.state.guardrail = CitationGuardrail(oracle=oracle)
    await pipeline.warmup()
    logger.info("models warmed up")
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
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/feedback")
@limiter.limit("20/minute")
async def post_feedback(request: Request, body: FeedbackBody):
    if _SUPABASE_URL and _SUPABASE_KEY:
        await _insert_feedback_supabase(body.query, body.answer, body.rating, body.category, body.comment)
    else:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _insert_feedback, body.query, body.answer, body.rating, body.category, body.comment)
    return {"ok": True}


@app.get("/search")
@limiter.limit("30/minute")
async def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500, description="The search query in English or Pali"),
    top_k: int = Query(default=10, ge=1, le=20, description="Number of results to return"),
    nikayas: Optional[List[str]] = Query(default=None, description="Filter by Nikaya (DN, MN, SN, AN, DHP, ITI)"),
):
    pipeline = request.app.state.pipeline
    filtered_nikayas = [n for n in nikayas if n in _VALID_NIKAYAS] if nikayas else None
    results = await pipeline.search(q, top_k=top_k, nikayas=filtered_nikayas)
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
    filtered_nikayas = [n for n in nikayas if n in _VALID_NIKAYAS] if nikayas else None

    async def event_stream():
        try:
            t0 = time.perf_counter()
            yield f"data: {json.dumps({'type': 'status', 'text': 'Searching the Canon…'})}\n\n"
            context = await request.app.state.pipeline.search(q, top_k=top_k, nikayas=filtered_nikayas)
            t1 = time.perf_counter()
            logger.info("stream/search: %.2fs", t1 - t0)
            context = [c for c in context if len(c.get("english", "").strip().split()) >= 4]
            yield f"data: {json.dumps({'type': 'status', 'text': 'Composing answer…'})}\n\n"
            async for event in request.app.state.pipeline.stream_synthesize(q, context):
                if event["type"] == "chunk":
                    yield f"data: {json.dumps(event)}\n\n"
                else:
                    logger.info("stream/synthesize: %.2fs", time.perf_counter() - t1)
                    yield f"data: {json.dumps({'type': 'status', 'text': 'Verifying sources…'})}\n\n"
                    verification = request.app.state.guardrail.process_response(event["text"], context)
                    yield f"data: {json.dumps({'type': 'done', 'query': q, 'answer': verification['text'], 'hallucinations': verification['hallucinations'], 'canonical_misses': verification['canonical_misses'], 'is_faithful': verification['is_faithful'], 'context': context})}\n\n"
        except Exception as exc:
            logger.error("stream error: %s", exc, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Search failed, please try again.'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
