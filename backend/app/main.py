import asyncio
import json
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse
from backend.app.services.search_pipeline import SearchPipeline
from backend.app.services.guardrail import CitationGuardrail
from backend.app.services.answer_composer import AnswerComposer
from backend.app.services.citation_oracle import CitationOracle
from backend.app.services.sutta_title_index import SuttaTitleIndex
from backend.app.services.bm25_retriever import BM25Retriever
from backend.app.services.passage_context import PassageStore
from backend.app.services.supabase_client import SupabaseRestClient
from backend.app.services.feedback_store import FeedbackWriter, SQLiteFeedbackStore, SupabaseFeedbackStore
from backend.app.services.share_store import ShareStore, SQLiteShareStore, SupabaseShareStore
from backend.app.services.share_receipt import sanitize_context, verify_receipt

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

_VALID_NIKAYAS = {"DN", "MN", "SN", "AN", "DHP", "ITI", "UD", "STNP", "THAG", "THIG", "KHP"}
# Share ids are uuid4().hex — exactly 32 lowercase hex chars. Anything else is
# rejected at the boundary before any storage call, so a crafted id can never
# reach the PostgREST filter string (defense-in-depth with the client encoding).
_SHARE_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_DUMPS_DIR = Path(__file__).parent.parent.parent / "data" / "dumps"
_DEFAULT_FEEDBACK_DB = Path(__file__).parent.parent.parent / "feedback.db"
_raw_supabase_url = os.environ.get("SUPABASE_URL") or ""
_SUPABASE_URL = _raw_supabase_url.split("/rest/")[0].rstrip("/") or None
_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
_SHARE_RECEIPT_SECRET = os.environ.get("SHARE_RECEIPT_SECRET", "")


class FeedbackBody(BaseModel):
    query: str = Field(max_length=600)
    answer: str = Field(max_length=20000)
    rating: Literal["up", "down"]
    category: Literal[
        "Doctrinally inaccurate",
        "Missing important nuance",
        "Not relevant to my question",
        "Sources don't support the answer",
        "Too vague",
    ] | None = None
    comment: str | None = Field(default=None, max_length=2000)


class ShareBody(BaseModel):
    query: str = Field(max_length=600)
    answer: str = Field(max_length=20000)
    context: list[dict]
    receipt: str


class ContactBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=10, max_length=5000)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", v):
            raise ValueError("Invalid email address")
        return v


@asynccontextmanager
async def lifespan(app: FastAPI):
    feedback_store: FeedbackWriter
    share_store: ShareStore
    if _SUPABASE_URL and _SUPABASE_KEY:
        supabase_client = SupabaseRestClient(_SUPABASE_URL, _SUPABASE_KEY)
        feedback_store = SupabaseFeedbackStore(supabase_client)
        share_store = SupabaseShareStore(supabase_client)
    else:
        # Resolved fresh on each startup (not a module-level constant) so a test
        # fixture's env var, set before TestClient triggers startup, takes effect
        # before any SQLite file is touched.
        db_path = Path(os.environ.get("SQLITE_DB_PATH", str(_DEFAULT_FEEDBACK_DB)))
        feedback_store = SQLiteFeedbackStore(db_path)
        share_store = SQLiteShareStore(db_path)
    oracle = CitationOracle(_DUMPS_DIR)
    title_index = SuttaTitleIndex.from_directory(_DUMPS_DIR)
    bm25_retriever = BM25Retriever.from_directory(_DUMPS_DIR)
    pipeline = SearchPipeline(
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
    guardrail = CitationGuardrail(oracle=oracle)
    passages = PassageStore.from_directory(_DUMPS_DIR)
    app.state.pipeline = pipeline
    app.state.guardrail = guardrail
    app.state.passages = passages
    app.state.feedback_store = feedback_store
    app.state.share_store = share_store
    app.state.composer = AnswerComposer(pipeline, guardrail, passages, title_index, _SHARE_RECEIPT_SECRET)
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
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        request.app.state.feedback_store.insert,
        body.query, body.answer, body.rating, body.category, body.comment,
    )
    return {"ok": True}


@app.post("/share")
async def post_share(request: Request, body: ShareBody):
    if not verify_receipt(body.query, body.answer, body.context, body.receipt, _SHARE_RECEIPT_SECRET):
        raise HTTPException(status_code=400, detail="Invalid receipt")
    context = sanitize_context(body.context)
    share_id = uuid.uuid4().hex
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, request.app.state.share_store.save, share_id, body.query, body.answer, context
    )
    return {"id": share_id}


@app.get("/share/{share_id}")
async def get_share(request: Request, share_id: str):
    # Reject malformed ids with the same 404 a genuine missing id gets, and do
    # it before any storage call, so a crafted id can't be used to tell
    # whether it was rejected here or merely not found in storage.
    if not _SHARE_ID_RE.match(share_id):
        raise HTTPException(status_code=404, detail="Not found")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, request.app.state.share_store.fetch, share_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Not found")
    return result


@app.post("/contact")
@limiter.limit("5/hour")
async def contact(request: Request, body: ContactBody):
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        logger.error("RESEND_API_KEY not set")
        raise HTTPException(status_code=500, detail="Email service unavailable")

    import resend as resend_client
    resend_client.api_key = api_key

    params: resend_client.Emails.SendParams = {
        # onboarding@resend.dev is Resend's shared sandbox sender: it will only
        # deliver to the Resend account owner's own verified address. Pointing
        # "to" anywhere else makes every submission fail with a 500.
        # TODO(eyal): switch to askthecanon@atomicmail.io once Resend is verified for it (#174)
        "from": "PCAIsearch <onboarding@resend.dev>",
        "to": ["tabibeyal101@gmail.com"],
        "reply_to": body.email,
        "subject": f"[PCAIsearch] Message from {body.name}",
        "text": f"Name: {body.name}\nEmail: {body.email}\n\nMessage:\n{body.message}",
    }
    try:
        await asyncio.get_event_loop().run_in_executor(None, resend_client.Emails.send, params)
    except Exception as exc:
        logger.error("Resend error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to send message")
    return {"ok": True}


@app.get("/synthesize")
@limiter.limit("10/minute")
async def synthesize(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500, description="The question to answer"),
    top_k: int = Query(default=10, ge=1, le=20, description="Number of context chunks to retrieve"),
    nikayas: list[str] | None = Query(default=None, description="Filter by Nikaya (DN, MN, SN, AN, DHP, ITI)"),
):
    filtered_nikayas = [n for n in nikayas if n in _VALID_NIKAYAS] if nikayas else None
    try:
        return await request.app.state.composer.answer(q, top_k=top_k, nikayas=filtered_nikayas)
    except Exception as exc:
        logger.error("synthesize error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed, please try again.")

@app.get("/stream")
@limiter.limit("10/minute")
async def stream(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500, description="The question to answer"),
    top_k: int = Query(default=15, ge=1, le=20, description="Number of context chunks to retrieve"),
    nikayas: list[str] | None = Query(default=None, description="Filter by Nikaya (DN, MN, SN, AN, DHP, ITI)"),
):
    filtered_nikayas = [n for n in nikayas if n in _VALID_NIKAYAS] if nikayas else None

    async def event_stream():
        try:
            async for event in request.app.state.composer.answer_stream(q, top_k=top_k, nikayas=filtered_nikayas):
                yield f"data: {json.dumps(event)}\n\n"
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
