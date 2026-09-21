"""The LLM provider seam: Groq credentials, and the startup check that makes a
retired model impossible to miss instead of silently degrading a search."""

import logging

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture(scope="module")
def pipeline():
    with patch("backend.app.services.search_pipeline.AsyncQdrantClient"), \
         patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        from backend.app.services.search_pipeline import SearchPipeline
        return SearchPipeline()


def _mock_llm(pipeline, error: Exception | None = None) -> AsyncMock:
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(side_effect=error)
    pipeline.llm = client
    return client


def test_client_is_built_for_groq():
    with patch("backend.app.services.search_pipeline.AsyncQdrantClient"), \
         patch("backend.app.services.search_pipeline.AsyncOpenAI") as client_cls:
        from backend.app.services.search_pipeline import SearchPipeline
        SearchPipeline()

    assert client_cls.call_args.kwargs["base_url"] == "https://api.groq.com/openai/v1"


@pytest.mark.asyncio
async def test_warmup_checks_both_models(pipeline, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-tests")
    client = _mock_llm(pipeline)

    with patch.object(pipeline.retriever.embedding_mgr, "encode"), \
         patch.object(pipeline.reranker.model, "predict"):
        await pipeline.warmup()

    checked = {call.kwargs["model"] for call in client.chat.completions.create.call_args_list}
    assert checked == {pipeline.llm_model, pipeline.expansion_model}


@pytest.mark.asyncio
async def test_startup_check_warns_when_a_model_is_retired(pipeline, monkeypatch, caplog):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-tests")
    _mock_llm(pipeline, error=RuntimeError("410 Gone"))

    with caplog.at_level(logging.WARNING):
        await pipeline._check_models()

    assert pipeline.llm_model in caplog.text


@pytest.mark.asyncio
async def test_startup_check_is_quiet_when_both_models_answer(pipeline, monkeypatch, caplog):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-tests")
    _mock_llm(pipeline)

    with caplog.at_level(logging.WARNING):
        await pipeline._check_models()

    assert "not answering" not in caplog.text


@pytest.mark.asyncio
async def test_startup_check_warns_when_the_key_is_missing(pipeline, monkeypatch, caplog):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    _mock_llm(pipeline)

    with caplog.at_level(logging.WARNING):
        await pipeline._check_models()

    assert "GROQ_API_KEY" in caplog.text
