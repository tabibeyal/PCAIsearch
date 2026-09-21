import logging
import time
from typing import Any

from backend.app.services.citation_support_check import (
    CitationSupportCheck,
    CitationSupportCheckError,
    find_checkable_citations,
    mark_unsupported,
)
from backend.app.services.guardrail import CitationGuardrail
from backend.app.services.passage_context import PassageStore
from backend.app.services.scope_guard import OUT_OF_SCOPE_MESSAGE, ScopeGuard, ScopeGuardError
from backend.app.services.search_pipeline import SearchPipeline
from backend.app.services.share_receipt import generate_receipt
from backend.app.services.sutta_title_index import SuttaTitleIndex

logger = logging.getLogger(__name__)


class AnswerComposer:
    """Owns the compose flow shared by /synthesize and /stream: scope guard ->
    search -> prepare_context (kept context) -> synthesize -> Guardrail ->
    attach passages/titles -> Receipt. Guardrail, Receipt, and the returned
    context all see the same kept-context list that was fed to synthesis.

    Raises on failure rather than swallowing exceptions — each route applies
    its own transport-appropriate error handling. The scope guard and the
    citation support check are the two exceptions: a guard or check failure
    (Jev slow, down, or rate-limiting) falls back to answering unguarded /
    publishing the citation unmarked rather than raising, so a third party
    outage never takes search down (#198, #208).
    """

    def __init__(
        self,
        pipeline: SearchPipeline,
        guardrail: CitationGuardrail,
        passages: PassageStore,
        title_index: SuttaTitleIndex,
        receipt_secret: str,
        scope_guard: ScopeGuard | None = None,
        citation_support_check: CitationSupportCheck | None = None,
    ) -> None:
        self.pipeline = pipeline
        self.guardrail = guardrail
        self.passages = passages
        self.title_index = title_index
        self.receipt_secret = receipt_secret
        self.scope_guard = scope_guard
        self.citation_support_check = citation_support_check

    async def answer(self, query: str, top_k: int, nikayas: list[str] | None = None) -> dict[str, Any]:
        if await self._is_out_of_scope(query):
            return self._out_of_scope_result(query)

        # The answer flow is canon-only: translator commentary is excluded at
        # retrieval time so every context slot is a usable canon passage (#102).
        context = await self.pipeline.search(
            query, top_k=top_k, nikayas=nikayas, exclude_commentary=True
        )
        kept = self.pipeline.prepare_context(context)
        raw_answer = await self.pipeline.synthesize(query, kept)
        return await self._finalize(query, kept, raw_answer)

    async def answer_stream(self, query: str, top_k: int, nikayas: list[str] | None = None):
        """Streaming counterpart to answer(): yields typed status/chunk/done
        event dicts, with done's payload matching answer()'s return shape.

        Raises rather than yielding an error event itself — same contract as
        answer(). An error event (or the stream simply ending without a done
        event) is terminal: any chunk text already sent must be treated as
        incomplete and discarded, never presented as the final answer.
        """
        if await self._is_out_of_scope(query):
            yield {"type": "done", **self._out_of_scope_result(query)}
            return

        t0 = time.perf_counter()
        yield {"type": "status", "text": "Searching the Canon…"}
        context = await self.pipeline.search(
            query, top_k=top_k, nikayas=nikayas, exclude_commentary=True
        )
        kept = self.pipeline.prepare_context(context)
        t1 = time.perf_counter()
        logger.info("stream/search: %.2fs", t1 - t0)

        yield {"type": "status", "text": "Composing answer…"}
        raw_answer = ""
        async for event in self.pipeline.stream_synthesize(query, kept):
            if event["type"] == "chunk":
                yield event
            else:
                raw_answer = event["text"]
        logger.info("stream/synthesize: %.2fs", time.perf_counter() - t1)

        yield {"type": "status", "text": "Verifying sources…"}
        yield {"type": "done", **await self._finalize(query, kept, raw_answer)}

    async def _is_out_of_scope(self, query: str) -> bool:
        if not self.scope_guard:
            return False
        try:
            return not await self.scope_guard.is_in_scope(query)
        except ScopeGuardError as exc:
            logger.warning("scope guard failed, answering unguarded: %s", exc)
            return False

    def _out_of_scope_result(self, query: str) -> dict[str, Any]:
        receipt = generate_receipt(query, OUT_OF_SCOPE_MESSAGE, [], self.receipt_secret)
        return {
            "query": query,
            "answer": OUT_OF_SCOPE_MESSAGE,
            "hallucinations": [],
            "canonical_misses": [],
            "is_faithful": True,
            "context": [],
            "receipt": receipt,
        }

    async def _finalize(self, query: str, kept: list[dict[str, Any]], raw_answer: str) -> dict[str, Any]:
        verification = self.guardrail.process_response(raw_answer, kept)
        text = await self._check_citation_support(kept, verification["text"])
        self._attach_passages(kept)
        self._attach_titles(kept)
        receipt = generate_receipt(query, text, kept, self.receipt_secret)

        return {
            "query": query,
            "answer": text,
            "hallucinations": verification["hallucinations"],
            "canonical_misses": verification["canonical_misses"],
            "is_faithful": verification["is_faithful"],
            "context": kept,
            "receipt": receipt,
        }

    async def _check_citation_support(self, kept: list[dict[str, Any]], text: str) -> str:
        """Extends the one CitationGuardrail branch that runs no content check
        at all: a citation whose ID was retrieved this turn. Same seam as
        _is_out_of_scope — a check failure publishes the
        citation unmarked rather than raising, because failing closed here
        would mean withholding an answer over a third-party outage, not over
        anything wrong with the answer itself.
        """
        if not self.citation_support_check:
            return text
        retrieved_ids = {chunk["id"] for chunk in kept if chunk.get("id")}
        passage_by_id = {
            chunk["id"]: chunk["english"] for chunk in kept if chunk.get("id") and chunk.get("english")
        }
        citations = find_checkable_citations(text, retrieved_ids, passage_by_id)
        if not citations:
            return text
        try:
            relations = await self.citation_support_check.check(citations)
        except CitationSupportCheckError as exc:
            logger.warning("citation support check failed, publishing citations unmarked: %s", exc)
            return text
        return mark_unsupported(text, citations, relations)

    def _attach_passages(self, context: list[dict[str, Any]]) -> None:
        # Leaves `english` untouched so synthesis and the guardrail are unaffected.
        for chunk in context:
            window = self.passages.passage(chunk.get("id", ""))
            if window:
                chunk["passage"] = window

    def _attach_titles(self, context: list[dict[str, Any]]) -> None:
        for chunk in context:
            chunk_id = chunk.get("id", "")
            sutta_key = chunk_id.rsplit(":", 1)[0].replace(" ", "")
            title = self.title_index.get_title_text(sutta_key)
            if title:
                chunk["title"] = title
            parts = self.title_index.get_title_parts(sutta_key)
            if parts:
                chunk["title_pali"], chunk["title_english"] = parts
