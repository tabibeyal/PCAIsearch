import logging
import time
from typing import Any

from backend.app.services.guardrail import CitationGuardrail
from backend.app.services.passage_context import PassageStore
from backend.app.services.search_pipeline import SearchPipeline
from backend.app.services.share_receipt import generate_receipt
from backend.app.services.sutta_title_index import SuttaTitleIndex

logger = logging.getLogger(__name__)


class AnswerComposer:
    """Owns the compose flow shared by /synthesize and /stream: search ->
    prepare_context (kept context) -> synthesize -> Guardrail -> attach
    passages/titles -> Receipt. Guardrail, Receipt, and the returned context
    all see the same kept-context list that was fed to synthesis.

    Raises on failure rather than swallowing exceptions — each route applies
    its own transport-appropriate error handling.
    """

    def __init__(
        self,
        pipeline: SearchPipeline,
        guardrail: CitationGuardrail,
        passages: PassageStore,
        title_index: SuttaTitleIndex,
        receipt_secret: str,
    ) -> None:
        self.pipeline = pipeline
        self.guardrail = guardrail
        self.passages = passages
        self.title_index = title_index
        self.receipt_secret = receipt_secret

    async def answer(self, query: str, top_k: int, nikayas: list[str] | None = None) -> dict[str, Any]:
        # The answer flow is canon-only: translator commentary is excluded at
        # retrieval time so every context slot is a usable canon passage (#102).
        context = await self.pipeline.search(
            query, top_k=top_k, nikayas=nikayas, exclude_commentary=True, policy="global_best"
        )
        kept = self.pipeline.prepare_context(context)
        raw_answer = await self.pipeline.synthesize(query, kept)
        return self._finalize(query, kept, raw_answer)

    async def answer_stream(self, query: str, top_k: int, nikayas: list[str] | None = None):
        """Streaming counterpart to answer(): yields typed status/chunk/done
        event dicts, with done's payload matching answer()'s return shape.

        Raises rather than yielding an error event itself — same contract as
        answer(). An error event (or the stream simply ending without a done
        event) is terminal: any chunk text already sent must be treated as
        incomplete and discarded, never presented as the final answer.
        """
        t0 = time.perf_counter()
        yield {"type": "status", "text": "Searching the Canon…"}
        context = await self.pipeline.search(
            query, top_k=top_k, nikayas=nikayas, exclude_commentary=True, policy="global_best"
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
        yield {"type": "done", **self._finalize(query, kept, raw_answer)}

    def _finalize(self, query: str, kept: list[dict[str, Any]], raw_answer: str) -> dict[str, Any]:
        verification = self.guardrail.process_response(raw_answer, kept)
        self._attach_passages(kept)
        self._attach_titles(kept)
        receipt = generate_receipt(query, verification["text"], kept, self.receipt_secret)

        return {
            "query": query,
            "answer": verification["text"],
            "hallucinations": verification["hallucinations"],
            "canonical_misses": verification["canonical_misses"],
            "is_faithful": verification["is_faithful"],
            "context": kept,
            "receipt": receipt,
        }

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
