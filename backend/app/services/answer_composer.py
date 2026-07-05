from typing import Any

from backend.app.services.guardrail import CitationGuardrail
from backend.app.services.passage_context import PassageStore
from backend.app.services.search_pipeline import SearchPipeline
from backend.app.services.share_receipt import generate_receipt
from backend.app.services.sutta_title_index import SuttaTitleIndex


def _attach_passages(context: list[dict[str, Any]], store: PassageStore) -> list[dict[str, Any]]:
    """Add a display-only `passage` field (cited verse + neighbors) where a
    citation would otherwise show as a lone line. Leaves `english` untouched so
    synthesis and the guardrail are unaffected."""
    for chunk in context:
        window = store.passage(chunk.get("id", ""))
        if window:
            chunk["passage"] = window
    return context


def _attach_titles(context: list[dict[str, Any]], title_index: SuttaTitleIndex) -> list[dict[str, Any]]:
    """Add a display-only `title` field (canonical sutta title) used by the
    copy-to-clipboard feature to expand citations to `[ID:Verse — Title]`."""
    for chunk in context:
        chunk_id = chunk.get("id", "")
        sutta_key = chunk_id.rsplit(":", 1)[0].replace(" ", "")
        title = title_index.get_title_text(sutta_key)
        if title:
            chunk["title"] = title
    return context


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
        context = await self.pipeline.search(query, top_k=top_k, nikayas=nikayas)
        kept = self.pipeline.prepare_context(context)

        raw_answer = await self.pipeline.synthesize(query, kept)
        verification = self.guardrail.process_response(raw_answer, kept)

        _attach_passages(kept, self.passages)
        _attach_titles(kept, self.title_index)
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
