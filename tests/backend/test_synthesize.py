import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call


@pytest.fixture
def pipeline():
    with patch("backend.app.services.search_pipeline.AsyncQdrantClient"):
        from backend.app.services.search_pipeline import SearchPipeline
        return SearchPipeline()


@pytest.fixture
def sample_context():
    return [
        {"id": "DN 1:1", "pali": "evam me sutaṃ", "english": "Thus have I heard"},
        {"id": "MN 10:5", "pali": "sammā-sati", "english": "Right Mindfulness"},
    ]


def _mock_llm(pipeline, reply: str) -> AsyncMock:
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=reply)]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    pipeline.llm = mock_client
    return mock_client


@pytest.mark.asyncio
async def test_synthesize_calls_claude_api(pipeline, sample_context):
    mock_client = _mock_llm(pipeline, "The opening verse is in [DN 1:1].")

    result = await pipeline.synthesize("What is the opening verse?", sample_context)

    mock_client.messages.create.assert_called_once()
    assert result == "The opening verse is in [DN 1:1]."


@pytest.mark.asyncio
async def test_synthesize_system_prompt_instructs_citation_format(pipeline, sample_context):
    mock_client = _mock_llm(pipeline, "Answer")

    await pipeline.synthesize("query", sample_context)

    kwargs = mock_client.messages.create.call_args.kwargs
    system = kwargs.get("system", "")
    system_text = (
        " ".join(b["text"] for b in system if isinstance(b, dict) and "text" in b)
        if isinstance(system, list) else system
    )
    assert "[" in system_text and ":" in system_text, \
        "System prompt must describe the [ID:Verse] citation format"


@pytest.mark.asyncio
async def test_synthesize_includes_all_context_ids_in_message(pipeline, sample_context):
    mock_client = _mock_llm(pipeline, "Answer")

    await pipeline.synthesize("query", sample_context)

    kwargs = mock_client.messages.create.call_args.kwargs
    messages = kwargs.get("messages", [])
    user_text = " ".join(
        block["text"] if isinstance(block, dict) else block
        for msg in messages if msg["role"] == "user"
        for block in (msg["content"] if isinstance(msg["content"], list) else [msg["content"]])
    )
    assert "DN 1:1" in user_text
    assert "MN 10:5" in user_text


@pytest.mark.asyncio
async def test_synthesize_uses_claude_model(pipeline, sample_context):
    mock_client = _mock_llm(pipeline, "Answer")

    await pipeline.synthesize("query", sample_context)

    model = mock_client.messages.create.call_args.kwargs.get("model", "")
    assert model.startswith("claude-"), f"Expected a Claude model, got: {model!r}"


@pytest.mark.asyncio
async def test_synthesize_uses_prompt_caching_on_system(pipeline, sample_context):
    mock_client = _mock_llm(pipeline, "Answer")

    await pipeline.synthesize("query", sample_context)

    system = mock_client.messages.create.call_args.kwargs.get("system", "")
    assert isinstance(system, list), "system must be a list of blocks to support cache_control"
    has_cache = any(
        isinstance(b, dict) and b.get("cache_control", {}).get("type") == "ephemeral"
        for b in system
    )
    assert has_cache, "At least one system block must have cache_control ephemeral"
