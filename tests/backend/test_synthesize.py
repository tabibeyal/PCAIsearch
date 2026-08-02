import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def pipeline():
    with patch("backend.app.services.search_pipeline.AsyncQdrantClient"), \
         patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        from backend.app.services.search_pipeline import SearchPipeline
        return SearchPipeline()


@pytest.fixture
def sample_context():
    return [
        {"id": "DN 1:1", "english": "Thus have I heard"},
        {"id": "MN 10:5", "english": "Right mindfulness is awareness of the present moment"},
    ]


def _mock_llm(pipeline, reply: str) -> AsyncMock:
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = reply
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    pipeline.llm = mock_client
    return mock_client


@pytest.mark.asyncio
async def test_synthesize_calls_llm(pipeline, sample_context):
    mock_client = _mock_llm(pipeline, "The opening verse is in [DN 1:1].")

    result = await pipeline.synthesize("What is the opening verse?", sample_context)

    mock_client.chat.completions.create.assert_called_once()
    assert result == "The opening verse is in [DN 1:1]."


@pytest.mark.asyncio
async def test_synthesize_system_prompt_instructs_citation_format(pipeline, sample_context):
    mock_client = _mock_llm(pipeline, "Answer")

    await pipeline.synthesize("query", sample_context)

    kwargs = mock_client.chat.completions.create.call_args.kwargs
    messages = kwargs.get("messages", [])
    system_text = next(
        (m["content"] for m in messages if m.get("role") == "system"), ""
    )
    assert "[" in system_text and ":" in system_text, \
        "System prompt must describe the [ID:Verse] citation format"


@pytest.mark.asyncio
async def test_synthesize_includes_all_context_ids_in_message(pipeline, sample_context):
    mock_client = _mock_llm(pipeline, "Answer")

    await pipeline.synthesize("query", sample_context)

    kwargs = mock_client.chat.completions.create.call_args.kwargs
    messages = kwargs.get("messages", [])
    user_text = next(
        (m["content"] for m in messages if m.get("role") == "user"), ""
    )
    assert "DN 1:1" in user_text
    assert "MN 10:5" in user_text


@pytest.mark.asyncio
async def test_synthesize_specifies_a_model(pipeline, sample_context):
    mock_client = _mock_llm(pipeline, "Answer")

    await pipeline.synthesize("query", sample_context)

    model = mock_client.chat.completions.create.call_args.kwargs.get("model", "")
    assert model, "synthesize must pass a non-empty model name to the LLM"


@pytest.mark.asyncio
async def test_synthesize_sends_system_and_user_messages(pipeline, sample_context):
    mock_client = _mock_llm(pipeline, "Answer")

    await pipeline.synthesize("query", sample_context)

    messages = mock_client.chat.completions.create.call_args.kwargs.get("messages", [])
    roles = [m["role"] for m in messages]
    assert "system" in roles, "Must include a system message"
    assert "user" in roles, "Must include a user message"


@pytest.mark.asyncio
async def test_synthesize_uses_1200_max_tokens(pipeline, sample_context):
    mock_client = _mock_llm(pipeline, "Answer")

    await pipeline.synthesize("query", sample_context)

    kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert kwargs["max_tokens"] == 1200


def test_system_prompt_requires_bullet_count_guidance():
    from backend.app.services.search_pipeline import _SYSTEM_PROMPT
    assert "2–5 bullets" in _SYSTEM_PROMPT


def test_system_prompt_requires_nikaya_diversity():
    from backend.app.services.search_pipeline import _SYSTEM_PROMPT
    assert "at least 3 different nikāyas" in _SYSTEM_PROMPT


def test_thanissaro_terms_rewrites_standard_rendering():
    from backend.app.services.search_pipeline import _apply_thanissaro_terms
    result = _apply_thanissaro_terms("Practise loving-kindness daily.", [])
    assert result == "Practise good will daily."


def test_thanissaro_terms_preserves_sentence_capitalisation():
    from backend.app.services.search_pipeline import _apply_thanissaro_terms
    result = _apply_thanissaro_terms("Wholesome acts bear fruit.", [])
    assert result == "Skillful acts bear fruit."


def test_thanissaro_terms_leaves_quoted_passage_wording_intact():
    from backend.app.services.search_pipeline import _apply_thanissaro_terms
    chunks = [{"english": "Such is the origination of this entire mass of stress & suffering."}]
    quote = "Such is the origination of this entire mass of stress & suffering."
    assert _apply_thanissaro_terms(quote, chunks) == quote


def test_thanissaro_terms_rewrites_own_prose_despite_quoted_use_elsewhere():
    from backend.app.services.search_pipeline import _apply_thanissaro_terms
    chunks = [{"english": "Such is the origination of this entire mass of stress & suffering."}]
    result = _apply_thanissaro_terms("The Buddha taught that suffering can end.", chunks)
    assert result == "The Buddha taught that stress can end."


def test_thanissaro_terms_collapses_pair_made_redundant_by_rewrite():
    from backend.app.services.search_pipeline import _apply_thanissaro_terms
    result = _apply_thanissaro_terms("The Buddha taught about suffering and stress.", [])
    assert result == "The Buddha taught about stress."


def test_thanissaro_terms_leaves_unlisted_words_alone():
    from backend.app.services.search_pipeline import _apply_thanissaro_terms
    result = _apply_thanissaro_terms("Right effort sustains the path.", [])
    assert result == "Right effort sustains the path."


def test_thanissaro_terms_does_not_match_inside_longer_word():
    from backend.app.services.search_pipeline import _apply_thanissaro_terms
    result = _apply_thanissaro_terms("The faithful lay followers gathered.", [])
    assert result == "The faithful lay followers gathered."


@pytest.mark.asyncio
async def test_synthesize_applies_thanissaro_terms(pipeline, sample_context):
    _mock_llm(pipeline, "Cultivate loving-kindness towards all beings.")

    result = await pipeline.synthesize("query", sample_context)

    assert result == "Cultivate good will towards all beings."


def _mock_llm_stream(pipeline, deltas: list[str]) -> None:
    async def _chunks():
        for d in deltas:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = d
            yield chunk

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_chunks())
    pipeline.llm = mock_client


@pytest.mark.asyncio
async def test_stream_synthesize_rewrites_terms_in_streamed_chunks(pipeline, sample_context):
    words = "Develop loving-kindness towards every being you meet today without exception".split()
    _mock_llm_stream(pipeline, [w + " " for w in words])

    events = [e async for e in pipeline.stream_synthesize("q", sample_context)]

    streamed = "".join(e["text"] for e in events if e["type"] == "chunk")
    assert "loving-kindness" not in streamed


@pytest.mark.asyncio
async def test_stream_synthesize_chunks_reassemble_to_final_text(pipeline, sample_context):
    words = "Develop loving-kindness towards every being you meet today without exception".split()
    _mock_llm_stream(pipeline, [w + " " for w in words])

    events = [e async for e in pipeline.stream_synthesize("q", sample_context)]

    streamed = "".join(e["text"] for e in events if e["type"] == "chunk")
    full = next(e["text"] for e in events if e["type"] == "full")
    assert streamed.strip() == full.strip()


@pytest.mark.asyncio
async def test_stream_synthesize_survives_rewrite_that_shortens_earlier_text(pipeline, sample_context):
    # 'suffering and stress' collapses to 'stress' once both halves are rewritten,
    # shortening text the stream may already have passed over.
    words = "Stress and suffering and stress arise from attachment to the aggregates and cease with it".split()
    _mock_llm_stream(pipeline, [w + " " for w in words])

    events = [e async for e in pipeline.stream_synthesize("q", sample_context)]

    streamed = "".join(e["text"] for e in events if e["type"] == "chunk")
    full = next(e["text"] for e in events if e["type"] == "full")
    assert streamed == full


@pytest.mark.asyncio
async def test_stream_synthesize_withholds_citation_bracket_until_closed(pipeline, sample_context):
    deltas = ["Mindfulness is taught widely across the canon in many places ",
              "[MN 10:1, DN 22:2, SN 47:3, AN 4.5:6]", " and beyond."]
    _mock_llm_stream(pipeline, deltas)

    events = [e async for e in pipeline.stream_synthesize("q", sample_context)]

    streamed = "".join(e["text"] for e in events if e["type"] == "chunk")
    assert streamed.count("MN 10:1") == 1 and "AN 4.5:6" not in streamed


def test_prepare_context_drops_short_english_chunk(pipeline):
    chunks = [
        {"id": "DN 1:1", "english": "Too short"},
        {"id": "MN 10:5", "english": "Right mindfulness is awareness of the present moment"},
    ]
    kept = pipeline.prepare_context(chunks)
    assert [c["id"] for c in kept] == ["MN 10:5"]


def test_prepare_context_dedups_identical_english_keeping_first(pipeline):
    chunks = [
        {"id": "DN 1:1", "english": "Right mindfulness is awareness of the moment"},
        {"id": "MN 10:5", "english": "Right mindfulness is awareness of the moment"},
    ]
    kept = pipeline.prepare_context(chunks)
    assert [c["id"] for c in kept] == ["DN 1:1"]
