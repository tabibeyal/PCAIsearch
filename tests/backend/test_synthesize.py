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
        {"id": "DN 1:1", "pali": "evam me sutaṃ", "english": "Thus have I heard"},
        {"id": "MN 10:5", "pali": "sammā-sati", "english": "Right Mindfulness"},
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
