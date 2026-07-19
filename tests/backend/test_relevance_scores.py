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


def test_filler_score_excluded_from_normalization_range():
    # The filler's -20.0 must not pull the floor down for the organic entries.
    scores = _relevance_scores([-5.0, -6.5, -20.0], [False, False, True])
    assert scores[0] == pytest.approx(_RELEVANCE_CEIL)
    assert scores[1] == pytest.approx(_RELEVANCE_FLOOR)
    assert scores[2] is None


def test_all_filler_set_returns_none_for_every_entry():
    scores = _relevance_scores([-5.0, -6.5], [True, True])
    assert scores == [None, None]


def test_filler_none_does_not_break_equal_organic_logits():
    # Organic entries all equal → both at ceiling; filler stays None.
    scores = _relevance_scores([-3.0, -3.0, -3.0], [False, False, True])
    assert scores[0] == _RELEVANCE_CEIL
    assert scores[1] == _RELEVANCE_CEIL
    assert scores[2] is None


def test_default_treats_all_entries_as_organic():
    # No is_filler arg: behaves like the pre-filler rank-normalization.
    scores = _relevance_scores([-7.2, -5.0, -6.5])
    assert scores[1] == pytest.approx(_RELEVANCE_CEIL)
    assert scores[0] == pytest.approx(_RELEVANCE_FLOOR)
