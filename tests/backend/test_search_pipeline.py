import pytest
from unittest.mock import AsyncMock, patch
from backend.app.services.search_pipeline import SearchPipeline, get_expansion_prompt
from backend.app.services.bm25_retriever import BM25Retriever
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.http import models


async def _make_pipeline_with_client(chunks: list) -> tuple:
    client = AsyncQdrantClient(":memory:")
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()
    pipeline.retriever.client = client
    pipeline.expand_query = AsyncMock(side_effect=lambda q, **_: [q])

    collection_name = "pali_canon"
    await client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=pipeline.retriever.embedding_mgr.dimension,
            distance=models.Distance.COSINE,
        ),
    )

    if chunks:
        points = [
            models.PointStruct(
                id=idx,
                vector=pipeline.retriever.embedding_mgr.encode(c['english']),
                payload=c,
            )
            for idx, c in enumerate(chunks)
        ]
        await client.upsert(collection_name=collection_name, points=points)

    return pipeline, client


@pytest.mark.asyncio
async def test_search_pipeline_retrieval():
    chunks = [
        {"id": "DN 1:1", "english": "Thus have I heard"},
        {"id": "DN 1:2", "english": "then"},
        {"id": "MN 10:1", "english": "Connected Discourses"},
    ]
    pipeline, _ = await _make_pipeline_with_client(chunks)

    results = await pipeline.search("Thus have I heard", top_k=1)

    assert len(results) == 1
    assert results[0]["id"] == "DN 1:1"
    assert results[0]["english"] == "Thus have I heard"


@pytest.mark.asyncio
async def test_search_pipeline_empty_results():
    pipeline, _ = await _make_pipeline_with_client([])

    results = await pipeline.search("something that doesn't exist", top_k=5)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_commentary_marker_passes_through_search():
    """A commentary-flagged chunk surfaces in search results with the marker
    intact, so the results API can label it (#101)."""
    chunks = [
        {"id": "DN 1:3", "english": "This sutta introduces the Buddha as a teacher", "section": "commentary"},
        {"id": "DN 1:4", "english": "Thus have I heard the Blessed One was dwelling"},
    ]
    pipeline, _ = await _make_pipeline_with_client(chunks)
    pipeline.bm25_retriever = BM25Retriever(chunks)

    results = await pipeline.search("This sutta introduces the Buddha", top_k=2)
    by_id = {r["id"]: r for r in results}

    assert by_id["DN 1:3"]["section"] == "commentary"


@pytest.mark.asyncio
async def test_canon_chunk_has_no_section_marker_in_search():
    chunks = [
        {"id": "DN 1:3", "english": "This sutta introduces the Buddha as a teacher", "section": "commentary"},
        {"id": "DN 1:4", "english": "Thus have I heard the Blessed One was dwelling"},
    ]
    pipeline, _ = await _make_pipeline_with_client(chunks)
    pipeline.bm25_retriever = BM25Retriever(chunks)

    results = await pipeline.search("Thus have I heard", top_k=2)
    by_id = {r["id"]: r for r in results}

    assert "section" not in by_id["DN 1:4"]


@pytest.mark.asyncio
async def test_answer_flow_excludes_commentary_from_results():
    """The answer-flow search path (exclude_commentary=True) drops commentary
    from both dense and BM25 retrieval, so context slots fill with canon (#102)."""
    chunks = [
        {"id": "DN 1:3", "english": "This sutta introduces the Buddha as a teacher", "section": "commentary"},
        {"id": "DN 1:4", "english": "Thus have I heard the Blessed One was dwelling"},
    ]
    pipeline, _ = await _make_pipeline_with_client(chunks)
    pipeline.bm25_retriever = BM25Retriever(chunks)

    results = await pipeline.search("This sutta introduces the Buddha", top_k=2, exclude_commentary=True)

    assert [r["id"] for r in results] == ["DN 1:4"]


@pytest.mark.asyncio
async def test_plain_search_still_returns_commentary_chunk():
    """The plain search path (exclude_commentary defaults to False) still
    surfaces commentary — only the answer flow is canon-only (#102)."""
    chunks = [
        {"id": "DN 1:3", "english": "This sutta introduces the Buddha as a teacher", "section": "commentary"},
        {"id": "DN 1:4", "english": "Thus have I heard the Blessed One was dwelling"},
    ]
    pipeline, _ = await _make_pipeline_with_client(chunks)
    pipeline.bm25_retriever = BM25Retriever(chunks)

    results = await pipeline.search("This sutta introduces the Buddha", top_k=2)

    assert "DN 1:3" in {r["id"] for r in results}


@pytest.mark.asyncio
async def test_search_with_bm25_surfaces_exact_match():
    """BM25 path surfaces a passage whose exact words match the query."""
    chunks = [
        {"id": "SN 56.11:1", "english": "noble eightfold path right view intention speech"},
        {"id": "DN 1:1", "english": "Thus have I heard at one time"},
        {"id": "MN 10:1", "english": "mindfulness contemplating body feelings mind"},
    ]
    pipeline, _ = await _make_pipeline_with_client(chunks)
    pipeline.bm25_retriever = BM25Retriever(chunks)

    results = await pipeline.search("noble eightfold path", top_k=3)
    ids = [r["id"] for r in results]
    assert "SN 56.11:1" in ids


@pytest.mark.asyncio
async def test_nikaya_filter_excludes_other_nikayas_from_final_results():
    """nikayas=["MN"] must exclude non-MN verses even after BM25+RRF fusion."""
    chunks = [
        {"id": "MN 10:1", "nikaya": "MN", "english": "right mindfulness body"},
        {"id": "MN 10:2", "nikaya": "MN", "english": "right mindfulness feelings"},
        {"id": "DN 1:1", "nikaya": "DN", "english": "right view thus heard"},
        {"id": "SN 22.59:1", "nikaya": "SN", "english": "right mindfulness impermanent form"},
    ]
    pipeline, _ = await _make_pipeline_with_client(chunks)
    pipeline.bm25_retriever = BM25Retriever(chunks)

    results = await pipeline.search("right mindfulness", top_k=5, nikayas=["MN"])
    non_mn = [r for r in results if not r["id"].startswith("MN ")]
    assert not non_mn, f"Non-MN results leaked through: {non_mn}"


@pytest.mark.asyncio
async def test_bm25_runs_on_all_expanded_queries():
    """BM25 must be called for every expanded query variant, not just the original."""
    from unittest.mock import MagicMock
    chunks = [{"id": "MN 10:1", "english": "foundations of mindfulness"}]
    pipeline, _ = await _make_pipeline_with_client(chunks)

    mock_bm25 = MagicMock()
    mock_bm25.retrieve.return_value = []
    pipeline.bm25_retriever = mock_bm25
    pipeline.expand_query = AsyncMock(return_value=["original query", "satipatthana meditation"])

    await pipeline.search("original query", top_k=5)

    called_queries = [call.args[0] for call in mock_bm25.retrieve.call_args_list]
    assert "satipatthana meditation" in called_queries, (
        f"BM25 must be called with expanded variant; got calls: {called_queries}"
    )


def test_search_pipeline_constructor_accepts_bm25_retriever():
    verses = [{"id": "MN 1:1", "english": "test verse"}]
    bm25 = BM25Retriever(verses)
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline(bm25_retriever=bm25)
    assert pipeline.bm25_retriever is bm25


@pytest.mark.asyncio
async def test_dense_results_use_rrf_fuse_multi_not_first_seen():
    """Pipeline must call rrf_fuse_multi on per-query dense results, not first-seen dedup."""
    chunks = [{"id": "MN 10:1", "english": "mindfulness body"}]
    pipeline, _ = await _make_pipeline_with_client(chunks)
    pipeline.expand_query = AsyncMock(return_value=["query one", "query two"])

    with patch("backend.app.services.search_pipeline.rrf_fuse_multi") as mock_multi:
        mock_multi.return_value = []
        await pipeline.search("mindfulness", top_k=5)

    mock_multi.assert_called_once()
    call_arg = mock_multi.call_args[0][0]
    assert isinstance(call_arg, list), "rrf_fuse_multi must receive a list of lists"
    assert len(call_arg) == 2, f"Expected 2 per-query result lists, got {len(call_arg)}"


def test_reranker_multi_uses_max_score_across_queries():
    """rerank_multi must return max score across all queries, not just the first."""
    from unittest.mock import MagicMock, patch
    import numpy as np
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()

    chunks = [
        {"id": "A", "english": "one"},
        {"id": "B", "english": "two"},
    ]
    call_count = [0]

    def fake_predict(pairs):
        call_count[0] += 1
        if call_count[0] == 1:
            return np.array([-10.0, 5.0])
        return np.array([9.0, -10.0])

    pipeline.reranker.model.predict = fake_predict

    result = pipeline.reranker.rerank_multi(["q1", "q2"], chunks)
    assert result[0]["id"] == "A", "A scores 9.0 on q2, should rank first"
    assert result[0]["rerank_score"] == 9.0
    assert result[1]["id"] == "B"
    assert result[1]["rerank_score"] == 5.0


@pytest.mark.asyncio
async def test_search_reranks_with_original_plus_dict_hints():
    """search must call rerank_multi with the original query merged with any
    curated English dictionary hint — NOT the LLM-expanded variants or Pāḷi terms."""
    chunks = [{"id": "MN 61:36", "english": "deliberate lie bad deed"}]
    pipeline, _ = await _make_pipeline_with_client(chunks)
    pipeline.expand_query = AsyncMock(return_value=["original", "llm variant 1", "llm variant 2",
                                                    "pali terms from dict", "english hint from dict"])

    captured = {}

    def fake_rerank_multi(queries, chunk_list):
        captured["queries"] = queries
        return chunk_list

    pipeline.reranker.rerank_multi = fake_rerank_multi

    with patch("backend.app.services.search_pipeline.lookup", return_value="musāvādā sacca"), \
         patch("backend.app.services.search_pipeline.lookup_english", return_value="not ashamed to tell a deliberate lie"):
        await pipeline.search("original", top_k=5)

    assert captured["queries"] == ["original not ashamed to tell a deliberate lie"]
    assert "musāvādā sacca" not in captured["queries"], "Pāḷi terms must not reach the reranker (cross-encoder is English-only)"
    assert "llm variant 1" not in captured["queries"], "LLM variants must not reach the reranker"
    assert "llm variant 2" not in captured["queries"]


def test_expansion_prompt_is_string_and_nonempty():
    prompt = get_expansion_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 50


def test_expansion_prompt_has_two_line_structure():
    prompt = get_expansion_prompt()
    assert "Line 1" in prompt
    assert "Line 2" in prompt


def test_expansion_prompt_mentions_pali_terms():
    prompt = get_expansion_prompt()
    assert "Pali" in prompt or "Pāli" in prompt or "Pāḷi" in prompt


def test_expansion_prompt_forbids_sutta_numbers():
    prompt = get_expansion_prompt()
    assert "sutta number" in prompt.lower() or "sutta numbers" in prompt.lower()


def test_search_pipeline_default_uses_v7():
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()
    assert pipeline.expansion_prompt == get_expansion_prompt


@pytest.mark.asyncio
async def test_expand_query_appends_dictionary_hit():
    """When lookup() matches, expand_query returns 3 variants with the Pāḷi string last."""
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()

    async def fake_create(**kwargs):
        from types import SimpleNamespace
        msg = SimpleNamespace(content="english vocab line\npali line from llm")
        choice = SimpleNamespace(message=msg)
        return SimpleNamespace(choices=[choice])

    pipeline.llm.chat.completions.create = fake_create

    with patch("backend.app.services.search_pipeline.lookup", return_value="avijjā paṭicca-samuppāda") as mock_lookup, \
         patch("backend.app.services.search_pipeline.lookup_english", return_value=None):
        result = await pipeline.expand_query("how does ignorance cause suffering")

    mock_lookup.assert_called_once_with("how does ignorance cause suffering")
    assert "avijjā paṭicca-samuppāda" in result
    assert len(result) == 4  # original + 2 LLM lines + 1 dict hit


@pytest.mark.asyncio
async def test_expand_query_strips_line_labels():
    """expand_query must strip 'Line 1:' / 'Line 2:' prefixes the model may emit."""
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()

    async def fake_create(**kwargs):
        from types import SimpleNamespace
        msg = SimpleNamespace(content="Line 1: speak false untruth Rahula\nLine 2: musāvādā sacca")
        choice = SimpleNamespace(message=msg)
        return SimpleNamespace(choices=[choice])

    pipeline.llm.chat.completions.create = fake_create

    with patch("backend.app.services.search_pipeline.lookup", return_value=None), \
         patch("backend.app.services.search_pipeline.lookup_english", return_value=None):
        result = await pipeline.expand_query("what is the one precept")

    assert "speak false untruth Rahula" in result
    assert "musāvādā sacca" in result
    assert not any(v.startswith("Line") for v in result)


@pytest.mark.asyncio
async def test_expand_query_no_dictionary_hit_unchanged():
    """When lookup() returns None, expand_query returns the normal 3 variants."""
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()

    async def fake_create(**kwargs):
        from types import SimpleNamespace
        msg = SimpleNamespace(content="english vocab line\npali line from llm")
        choice = SimpleNamespace(message=msg)
        return SimpleNamespace(choices=[choice])

    pipeline.llm.chat.completions.create = fake_create

    with patch("backend.app.services.search_pipeline.lookup", return_value=None), \
         patch("backend.app.services.search_pipeline.lookup_english", return_value=None):
        result = await pipeline.expand_query("what is a good recipe for bread")

    assert len(result) == 3  # original + 2 LLM lines, no dict hit


@pytest.mark.asyncio
async def test_expand_query_appends_english_hint():
    """When lookup_english() matches, expand_query appends the English hint after the Pāḷi hit."""
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()

    async def fake_create(**kwargs):
        from types import SimpleNamespace
        msg = SimpleNamespace(content="english vocab line\npali line from llm")
        choice = SimpleNamespace(message=msg)
        return SimpleNamespace(choices=[choice])

    pipeline.llm.chat.completions.create = fake_create

    with patch("backend.app.services.search_pipeline.lookup", return_value="musāvādā sacca"), \
         patch("backend.app.services.search_pipeline.lookup_english", return_value="not ashamed to tell a deliberate lie no bad deed") as mock_en:
        result = await pipeline.expand_query("one precept never break")

    mock_en.assert_called_once_with("one precept never break")
    assert "not ashamed to tell a deliberate lie no bad deed" in result
    assert len(result) == 5  # original + 2 LLM lines + pali + english hint


@pytest.mark.asyncio
async def test_expand_query_falls_back_to_original_on_api_error():
    """When the expansion model call fails, expand_query returns the original query
    plus any dictionary hits — so search still works rather than crashing."""
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()

    async def failing_create(**kwargs):
        raise RuntimeError("NVIDIA API unavailable")

    pipeline.llm.chat.completions.create = failing_create

    with patch("backend.app.services.search_pipeline.lookup", return_value="avijjā"), \
         patch("backend.app.services.search_pipeline.lookup_english", return_value=None):
        result = await pipeline.expand_query("how does ignorance cause suffering")

    assert result[0] == "how does ignorance cause suffering"
    assert "avijjā" in result
    assert len(result) == 2


def test_expansion_prompt_v7_contains_reference_block():
    prompt = get_expansion_prompt()
    assert "paṭicca-samuppāda" in prompt
    assert "kakacūpama" in prompt
    assert "sigālovāda" in prompt


def test_expansion_prompt_v7_has_rahula_entry():
    prompt = get_expansion_prompt()
    assert "Rahula" in prompt
    assert "speak false untruth" in prompt


def test_expansion_prompt_v7_translates_non_english():
    prompt = get_expansion_prompt()
    assert "translate" in prompt.lower()
    assert "English" in prompt
    assert "deva" in prompt
    assert "should a monk feel anger" in prompt


@pytest.mark.asyncio
async def test_search_trims_candidates_before_reranking():
    """The cross-encoder reranker must receive a bounded candidate set,
    not the full fused result list, to keep CPU reranking fast."""
    pipeline, _ = await _make_pipeline_with_client([])

    # Return distinct chunks per retrieval call so the fused candidate list is
    # far larger than the final top_k. Without trimming, the reranker scores all of them.
    call_idx = 0
    async def fake_retrieve(*args, **kwargs):
        nonlocal call_idx
        call_idx += 1
        start = (call_idx - 1) * 50 + 1
        return [{"id": f"DN {i}:1", "english": f"chunk {i}"} for i in range(start, start + 50)]

    pipeline.retriever.retrieve = fake_retrieve
    pipeline.expand_query = AsyncMock(return_value=["query", "variant one", "variant two"])

    captured = {}

    def fake_rerank_multi(queries, chunk_list):
        captured["chunk_count"] = len(chunk_list)
        return chunk_list

    pipeline.reranker.rerank_multi = fake_rerank_multi

    await pipeline.search("query", top_k=5)

    # Per-bucket budget is max(retrieval_k*2, 100); with top_k=5 this means
    # at most 100 chunks should reach the reranker.
    assert captured["chunk_count"] <= 100


def test_expansion_prompt_v7_has_foam_simile_entry():
    prompt = get_expansion_prompt()
    assert "foam" in prompt
    assert "bubble" in prompt
    assert "vacuous" in prompt or "hollow" in prompt
    assert "pheṇapiṇḍa" in prompt


def test_system_prompt_prohibits_existence_denial():
    from backend.app.services.search_pipeline import _SYSTEM_PROMPT
    assert "NEVER DENY EXISTENCE" in _SYSTEM_PROMPT
    assert "couldn't find this in the retrieved passages" in _SYSTEM_PROMPT


def test_search_pipeline_uses_v7_by_default():
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()
    assert pipeline.expansion_prompt == get_expansion_prompt


def test_system_prompt_has_out_of_scope_guard():
    from backend.app.services.search_pipeline import _SYSTEM_PROMPT
    assert "OUT OF SCOPE" in _SYSTEM_PROMPT
    assert "outside the scope of this search engine" in _SYSTEM_PROMPT
    assert "arithmetic" in _SYSTEM_PROMPT or "cooking" in _SYSTEM_PROMPT
    assert "anger" in _SYSTEM_PROMPT or "grief" in _SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_multi_nikaya_search_includes_results_from_each_nikaya():
    """Searching SN+DHP must include DHP passages in the retrieval pool.

    Root cause fixed: combined filter let large nikayas (SN) crowd out small
    ones (DHP) from the retrieval pool entirely. The fix retrieves per-nikaya
    in parallel so each nikaya gets its own retrieval budget.

    The reranker is stubbed to preserve insertion order so the test only
    verifies retrieval behaviour, not cross-encoder scoring.
    """
    from unittest.mock import AsyncMock

    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()

    pipeline.expand_query = AsyncMock(return_value=["meditation"])
    # Stub reranker so ML scoring doesn't reorder the retrieval pool
    pipeline.reranker.rerank_multi = lambda queries, chunks: [{**c, "rerank_score": 0.0} for c in chunks]

    # 5 SN + 5 DHP results. Per-nikaya retrieval gives each its own 5-item pool.
    # The combined pool of 10 fits within top_k=10 so both must appear.
    sn_results = [
        {"id": f"SN 1.{i}:1", "nikaya": "SN", "english": f"meditation mindfulness {i}", "score": 0.9 - i * 0.01}
        for i in range(5)
    ]
    dhp_results = [
        {"id": f"DHP {i}:1", "nikaya": "DHP", "english": f"mind calm verse {i}", "score": 0.85 - i * 0.01}
        for i in range(5)
    ]

    async def fake_retrieve(query, top_k, nikayas=None, exclude_commentary=False):
        if nikayas == ["SN"]:
            return sn_results[:top_k]
        if nikayas == ["DHP"]:
            return dhp_results[:top_k]
        # Combined path: would return only SN (simulates the old crowding bug)
        return sn_results[:top_k]

    pipeline.retriever.retrieve = AsyncMock(side_effect=fake_retrieve)

    results = await pipeline.search("meditation", top_k=10, nikayas=["SN", "DHP"])
    result_nikayas = {r["id"].split()[0] for r in results}
    assert "DHP" in result_nikayas, (
        f"DHP results absent from SN+DHP search; got nikaya prefixes: {result_nikayas}"
    )
    assert "SN" in result_nikayas


def test_expansion_prompt_v7_has_named_similes():
    prompt = get_expansion_prompt()
    assert "near shore far shore raft" in prompt          # raft simile MN 22
    assert "arrow thickly smeared poison" in prompt       # poisoned arrow MN 63
    assert "arched harp strings tuned too tight" in prompt  # lute string AN 6.55
    assert "one-eyed turtle" in prompt                    # blind turtle SN 56.48
    assert "rosewood leaves handful" in prompt            # handful of leaves SN 56.31
    assert "second arrow" in prompt                       # two arrows SN 36.6
    assert "burning fire greed hate delusion" in prompt   # fire sermon SN 35.28
    assert "kullūpama" in prompt
    assert "salla" in prompt
    assert "vīṇā" in prompt
    assert "chiggaḷa" in prompt
    assert "paṭisota" in prompt
    assert "lump of salt" in prompt
    assert "rub two sticks" in prompt
    assert "foolish cook" in prompt
    assert "bathroom attendant" in prompt
    assert "native gold" in prompt and "crucible" in prompt
    assert "large peg finer peg" in prompt
    assert "cow udder" in prompt or "pulling horn" in prompt
    assert "pole acrobat" in prompt
    assert "ocean one taste" in prompt or "taste of salt" in prompt
    assert "blue water lilies" in prompt
    assert "your own island" in prompt or "island refuge" in prompt
    assert "six gates" in prompt and "gatekeeper" in prompt
    assert "dyed water" in prompt or "red lac" in prompt
async def _make_pipeline_with_rerank_scores(
    chunks: list,
    scores_by_id: dict,
) -> SearchPipeline:
    """In-memory pipeline whose reranker returns deterministic scores.

    BM25 is bypassed by default (empty results) so the small fixture does not
    introduce fusion ties that would override the intended rerank order.
    """
    from unittest.mock import MagicMock

    pipeline, _ = await _make_pipeline_with_client(chunks)
    # Disable BM25 by setting it to None so fusion is dense-only and predictable.
    pipeline.bm25_retriever = None

    def fake_rerank_multi(queries, cands):
        return sorted(
            [{**c, "rerank_score": scores_by_id.get(c["id"], 0.0)} for c in cands],
            key=lambda c: c["rerank_score"],
            reverse=True,
        )

    pipeline.reranker = MagicMock()
    pipeline.reranker.rerank_multi = fake_rerank_multi
    return pipeline


_POLICY_FIXTURE = {
    "chunks": [
        {"id": "DN 1:1", "nikaya": "DN", "english": "DN passage high"},
        {"id": "MN 1:1", "nikaya": "MN", "english": "MN passage high"},
        {"id": "MN 1:2", "nikaya": "MN", "english": "MN passage medium"},
        {"id": "DN 1:2", "nikaya": "DN", "english": "DN passage low"},
    ],
    # BM25 is disabled so the final order is driven by the rerank score map alone.
    "scores": {"DN 1:1": 4.0, "MN 1:1": 3.0, "MN 1:2": 2.0, "DN 1:2": 1.0},
}


@pytest.mark.asyncio
async def test_round_robin_policy_interleaves_buckets():
    """Default policy alternates one result from each selected nikāya."""
    fixture = _POLICY_FIXTURE
    pipeline = await _make_pipeline_with_rerank_scores(fixture["chunks"], fixture["scores"])

    results = await pipeline.search("passage", top_k=3, nikayas=["DN", "MN"])

    assert [r["id"] for r in results] == ["DN 1:1", "MN 1:1", "DN 1:2"]


@pytest.mark.asyncio
async def test_global_best_policy_takes_top_reranked_chunks():
    """global_best ignores nikāya buckets and takes the highest rerank scores."""
    fixture = _POLICY_FIXTURE
    pipeline = await _make_pipeline_with_rerank_scores(fixture["chunks"], fixture["scores"])

    results = await pipeline.search(
        "passage", top_k=3, nikayas=["DN", "MN"], policy="global_best"
    )

    assert [r["id"] for r in results] == ["DN 1:1", "MN 1:1", "MN 1:2"]


@pytest.mark.asyncio
async def test_relevance_floor_policy_skips_weak_bucket_chunks():
    """relevance_floor skips chunks whose score is below ratio * best_score."""
    fixture = _POLICY_FIXTURE
    pipeline = await _make_pipeline_with_rerank_scores(fixture["chunks"], fixture["scores"])

    results = await pipeline.search(
        "passage", top_k=3, nikayas=["DN", "MN"], policy="relevance_floor:0.6"
    )

    # floor = 0.6 * 4.0 = 2.4; MN 1:2 (2.0) and DN 1:2 (1.0) are dropped.
    assert [r["id"] for r in results] == ["DN 1:1", "MN 1:1"]


@pytest.mark.asyncio
async def test_relevance_floor_policy_with_high_threshold_can_empty_buckets():
    """A strict floor may leave a selected nikāya with no qualifying chunks."""
    fixture = _POLICY_FIXTURE
    pipeline = await _make_pipeline_with_rerank_scores(fixture["chunks"], fixture["scores"])

    results = await pipeline.search(
        "passage", top_k=3, nikayas=["DN", "MN"], policy="relevance_floor:0.9"
    )

    # floor = 0.9 * 4.0 = 3.6; only DN 1:1 qualifies.
    assert [r["id"] for r in results] == ["DN 1:1"]


@pytest.mark.asyncio
@pytest.mark.parametrize("policy", ["round_robin", "global_best", "relevance_floor:0.3"])
async def test_single_nikaya_policies_return_same_order(policy: str):
    """With only one bucket all policies reduce to the reranked top-k."""
    chunks = [
        {"id": "MN 1:1", "nikaya": "MN", "english": "MN passage high"},
        {"id": "MN 1:2", "nikaya": "MN", "english": "MN passage medium"},
        {"id": "MN 1:3", "nikaya": "MN", "english": "MN passage low"},
    ]
    scores = {"MN 1:1": 3.0, "MN 1:2": 2.0, "MN 1:3": 1.0}
    pipeline = await _make_pipeline_with_rerank_scores(chunks, scores)

    results = await pipeline.search("passage", top_k=3, nikayas=["MN"], policy=policy)

    assert [r["id"] for r in results] == ["MN 1:1", "MN 1:2", "MN 1:3"]


@pytest.mark.asyncio
async def test_unknown_policy_raises_value_error():
    chunks = [{"id": "MN 1:1", "nikaya": "MN", "english": "MN passage"}]
    pipeline = await _make_pipeline_with_rerank_scores(chunks, {"MN 1:1": 1.0})

    with pytest.raises(ValueError, match="Unknown search policy"):
        await pipeline.search("passage", top_k=1, nikayas=["MN"], policy="bogus")


@pytest.mark.asyncio
async def test_invalid_relevance_floor_policy_raises_value_error():
    chunks = [{"id": "MN 1:1", "nikaya": "MN", "english": "MN passage"}]
    pipeline = await _make_pipeline_with_rerank_scores(chunks, {"MN 1:1": 1.0})

    with pytest.raises(ValueError, match="Invalid relevance_floor policy"):
        await pipeline.search("passage", top_k=1, nikayas=["MN"], policy="relevance_floor:bad")
