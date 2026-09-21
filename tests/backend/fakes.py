from datetime import datetime, timezone
from typing import Any

from backend.app.services.citation_support_check import CitationSupportCheckError
from backend.app.services.scope_guard import ScopeGuardError
from backend.app.services.search_pipeline import SearchPipeline


class FakeSupabaseRestClient:
    """Behaves like the real Supabase PostgREST API against an in-memory
    table, instead of just recording calls — so tests can assert on actual
    behavior rather than on the shape of the request made.

    Mirrors SupabaseRestClient's structured-filter signature: callers pass
    `eq`/`is_null`/`select`/`order` kwargs, never a pre-assembled filter
    string, so the fake filters in-memory the same way the real client
    builds an encoded query string.
    """

    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {}

    def post(self, table: str, payload: dict[str, Any], *, error_label: str) -> None:
        rows = self._tables.setdefault(table, [])
        row = dict(payload)
        row.setdefault("id", len(rows) + 1)
        row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        rows.append(row)

    def get(
        self,
        table: str,
        *,
        eq: dict[str, Any] | None = None,
        is_null: list[str] | None = None,
        select: list[str] | None = None,
        order: tuple[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        rows = [r for r in self._tables.get(table, []) if _matches(r, eq, is_null)]
        if order:
            field, direction = order
            rows.sort(key=lambda r: r.get(field), reverse=direction == "desc")
        if select:
            rows = [{f: r.get(f) for f in select} for r in rows]
        return rows

    def patch(
        self,
        table: str,
        payload: dict[str, Any],
        *,
        eq: dict[str, Any] | None = None,
        is_null: list[str] | None = None,
    ) -> None:
        for row in self._tables.get(table, []):
            if _matches(row, eq, is_null):
                row.update(payload)


def _matches(
    row: dict[str, Any], eq: dict[str, Any] | None, is_null: list[str] | None
) -> bool:
    if eq:
        if any(str(row.get(col)) != str(val) for col, val in eq.items()):
            return False
    if is_null:
        if any(row.get(col) is not None for col in is_null):
            return False
    return True


class FakePipeline:
    """Stands in for SearchPipeline's network boundary (Qdrant + LLM) in
    AnswerComposer tests. prepare_context is the real, pure SearchPipeline
    logic reused as-is — faking it would mean the kept-context invariant is
    never really exercised."""

    prepare_context = staticmethod(SearchPipeline.prepare_context)

    def __init__(self, context: list[dict[str, Any]], answer: str) -> None:
        self._context = context
        self._answer = answer
        self.search_calls: list[dict[str, Any]] = []
        self.synthesize_contexts: list[list[dict[str, Any]]] = []

    async def search(
        self,
        query: str,
        top_k: int,
        nikayas: list[str] | None = None,
        exclude_commentary: bool = False,
    ) -> list[dict[str, Any]]:
        self.search_calls.append({"query": query, "top_k": top_k, "nikayas": nikayas, "exclude_commentary": exclude_commentary})
        return self._context

    async def synthesize(self, query: str, context_chunks: list[dict[str, Any]]) -> str:
        self.synthesize_contexts.append(context_chunks)
        return self._answer

    async def stream_synthesize(self, query: str, context_chunks: list[dict[str, Any]]):
        self.synthesize_contexts.append(context_chunks)
        for word in self._answer.split(" "):
            yield {"type": "chunk", "text": word + " "}
        yield {"type": "full", "text": self._answer}


class FakeScopeGuard:
    """Stands in for ScopeGuard in AnswerComposer tests: returns a fixed
    verdict, or raises ScopeGuardError if constructed with raises=True."""

    def __init__(self, in_scope: bool = True, raises: bool = False) -> None:
        self._in_scope = in_scope
        self._raises = raises
        self.queries: list[str] = []

    async def is_in_scope(self, query: str) -> bool:
        self.queries.append(query)
        if self._raises:
            raise ScopeGuardError("guard unavailable")
        return self._in_scope


class FakeCitationSupportCheck:
    """Stands in for CitationSupportCheck in AnswerComposer tests: returns a
    fixed relation for every citation in the batch, or raises
    CitationSupportCheckError if constructed with raises=True."""

    def __init__(self, relation: str = "supports", raises: bool = False) -> None:
        self._relation = relation
        self._raises = raises
        self.batches: list[list[dict[str, Any]]] = []

    async def check(self, citations: list[dict[str, Any]]) -> list[str]:
        self.batches.append(citations)
        if self._raises:
            raise CitationSupportCheckError("check unavailable")
        return [self._relation] * len(citations)


class RaisingFakePipeline:
    """FakePipeline whose search() raises, for asserting AnswerComposer
    propagates failures instead of swallowing them."""

    async def search(
        self,
        query: str,
        top_k: int,
        nikayas: list[str] | None = None,
        exclude_commentary: bool = False,
    ) -> list[dict[str, Any]]:
        raise RuntimeError("search failed")


class MidStreamRaisingFakePipeline:
    """FakePipeline whose stream_synthesize() raises after yielding a chunk,
    for asserting AnswerComposer.answer_stream propagates mid-generator
    failures instead of swallowing them."""

    def __init__(self, context: list[dict[str, Any]]) -> None:
        self._context = context

    async def search(
        self,
        query: str,
        top_k: int,
        nikayas: list[str] | None = None,
        exclude_commentary: bool = False,
    ) -> list[dict[str, Any]]:
        return self._context

    prepare_context = staticmethod(SearchPipeline.prepare_context)

    async def stream_synthesize(self, query: str, context_chunks: list[dict[str, Any]]):
        yield {"type": "chunk", "text": "partial "}
        raise RuntimeError("synthesis failed")
