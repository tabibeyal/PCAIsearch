import pytest
from unittest.mock import AsyncMock, patch
from backend.app.services.search_pipeline import SearchPipeline, ExpansionPrompt
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
                vector=pipeline.retriever.embedding_mgr.encode(f"{c['pali']} {c['english']}"),
                payload=c,
            )
            for idx, c in enumerate(chunks)
        ]
        await client.upsert(collection_name=collection_name, points=points)

    return pipeline, client


@pytest.mark.asyncio
async def test_search_pipeline_retrieval():
    chunks = [
        {"id": "DN 1:1", "pali": "evam me sutaṃ", "english": "Thus have I heard"},
        {"id": "DN 1:2", "pali": "tada", "english": "then"},
        {"id": "MN 10:1", "pali": "Samyutta", "english": "Connected Discourses"},
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
async def test_search_with_bm25_surfaces_exact_match():
    """BM25 path surfaces a passage whose exact words match the query."""
    chunks = [
        {"id": "SN 56.11:1", "pali": "", "english": "noble eightfold path right view intention speech"},
        {"id": "DN 1:1", "pali": "evam", "english": "Thus have I heard at one time"},
        {"id": "MN 10:1", "pali": "citta", "english": "mindfulness contemplating body feelings mind"},
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
        {"id": "MN 10:1", "nikaya": "MN", "pali": "citta", "english": "right mindfulness body"},
        {"id": "MN 10:2", "nikaya": "MN", "pali": "vedana", "english": "right mindfulness feelings"},
        {"id": "DN 1:1", "nikaya": "DN", "pali": "evam", "english": "right view thus heard"},
        {"id": "SN 22.59:1", "nikaya": "SN", "pali": "rupam", "english": "right mindfulness impermanent form"},
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
    chunks = [{"id": "MN 10:1", "pali": "", "english": "foundations of mindfulness"}]
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
    verses = [{"id": "MN 1:1", "pali": "", "english": "test verse"}]
    bm25 = BM25Retriever(verses)
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline(bm25_retriever=bm25)
    assert pipeline.bm25_retriever is bm25


@pytest.mark.asyncio
async def test_dense_results_use_rrf_fuse_multi_not_first_seen():
    """Pipeline must call rrf_fuse_multi on per-query dense results, not first-seen dedup."""
    chunks = [{"id": "MN 10:1", "pali": "", "english": "mindfulness body"}]
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
        {"id": "A", "pali": "", "english": "one"},
        {"id": "B", "pali": "", "english": "two"},
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
    """search must call rerank_multi with the original query and curated
    dictionary hints only — NOT the LLM-expanded variants."""
    chunks = [{"id": "MN 61:36", "pali": "", "english": "deliberate lie bad deed"}]
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

    assert "original" in captured["queries"]
    assert "not ashamed to tell a deliberate lie" in captured["queries"]
    assert "musāvādā sacca" not in captured["queries"], "Pāḷi terms must not reach the reranker (cross-encoder is English-only)"
    assert "llm variant 1" not in captured["queries"], "LLM variants must not reach the reranker"
    assert "llm variant 2" not in captured["queries"]


def test_expansion_prompt_v2_exists():
    prompt = ExpansionPrompt("v2").get_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 50


def test_expansion_prompt_v2_has_two_line_structure():
    prompt = ExpansionPrompt("v2").get_prompt()
    assert "Line 1" in prompt
    assert "Line 2" in prompt


def test_expansion_prompt_v2_mentions_pali_terms():
    prompt = ExpansionPrompt("v2").get_prompt()
    assert "Pali" in prompt or "Pāli" in prompt or "Pāḷi" in prompt


def test_expansion_prompt_v2_forbids_sutta_numbers():
    prompt = ExpansionPrompt("v2").get_prompt()
    assert "sutta number" in prompt.lower() or "sutta numbers" in prompt.lower()


def test_search_pipeline_default_uses_v7():
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()
    assert pipeline.expansion_prompt.version == "v7"


def test_expansion_prompt_raises_on_unknown_version():
    with pytest.raises(ValueError, match="Unknown expansion prompt version"):
        ExpansionPrompt("v99").get_prompt()


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


def test_expansion_prompt_v3_contains_reference_block():
    prompt = ExpansionPrompt("v3").get_prompt()
    assert "paṭicca-samuppāda" in prompt
    assert "kakacūpama" in prompt
    assert "sigālovāda" in prompt


def test_expansion_prompt_v4_contains_example_and_reference_block():
    prompt = ExpansionPrompt("v4").get_prompt()
    assert "avoid extremes" in prompt
    assert "paṭicca-samuppāda" in prompt
    assert "kakacūpama" in prompt
    assert "No labels" in prompt or "no labels" in prompt.lower()


def test_expansion_prompt_v5_contains_english_passage_hints():
    prompt = ExpansionPrompt("v5").get_prompt()
    assert "with ignorance as condition" in prompt
    assert "tradition hearsay scripture" in prompt
    assert "two-handled saw bandits" in prompt
    assert "six directions parents" in prompt
    assert "form inconstant stress suffering not-self" in prompt


def test_expansion_prompt_v6_has_second_example_and_rahula_entry():
    prompt = ExpansionPrompt("v6").get_prompt()
    assert "should a monk feel anger" in prompt
    assert "two-handed saw bandits cut limbs" in prompt
    assert "Rahula" in prompt
    assert "speak false untruth" in prompt
    assert "NOT to rely on" in prompt or "not to rely on" in prompt.lower()


def test_expansion_prompt_v7_translates_non_english():
    prompt = ExpansionPrompt("v7").get_prompt()
    assert "translate" in prompt.lower()
    assert "English" in prompt
    assert "deva" in prompt
    assert "should a monk feel anger" in prompt


def test_expansion_prompt_v7_has_foam_simile_entry():
    prompt = ExpansionPrompt("v7").get_prompt()
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
    assert pipeline.expansion_prompt.version == "v7"


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
        {"id": f"SN 1.{i}:1", "nikaya": "SN", "pali": "", "english": f"meditation mindfulness {i}", "score": 0.9 - i * 0.01}
        for i in range(5)
    ]
    dhp_results = [
        {"id": f"DHP {i}:1", "nikaya": "DHP", "pali": "", "english": f"mind calm verse {i}", "score": 0.85 - i * 0.01}
        for i in range(5)
    ]

    async def fake_retrieve(query, top_k, nikayas=None):
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
    prompt = ExpansionPrompt("v7").get_prompt()
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
