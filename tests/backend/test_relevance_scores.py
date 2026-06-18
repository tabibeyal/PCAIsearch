import pytest

from backend.app.services.search_pipeline import (
    _RELEVANCE_CEIL,
    _RELEVANCE_FLOOR,
    _relevance_scores,
)


def test_best_logit_maps_to_ceiling():
    scores = _relevance_scores([-7.2, -5.0, -6.5])
    assert scores[1] == pytest.approx(_RELEVANCE_CEIL)


def test_worst_logit_maps_to_floor():
    scores = _relevance_scores([-7.2, -5.0, -6.5])
    assert scores[0] == pytest.approx(_RELEVANCE_FLOOR)


def test_deeply_negative_logits_still_yield_high_top_score():
    # Regression: sigmoid(logit) collapsed these to ~1%; the top match must read high.
    scores = _relevance_scores([-5.0, -6.5, -7.2])
    assert scores[0] == pytest.approx(_RELEVANCE_CEIL)


def test_equal_logits_all_map_to_ceiling():
    scores = _relevance_scores([-3.0, -3.0, -3.0])
    assert scores == [_RELEVANCE_CEIL, _RELEVANCE_CEIL, _RELEVANCE_CEIL]


def test_empty_input_returns_empty():
    assert _relevance_scores([]) == []
