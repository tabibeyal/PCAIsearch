import json
import pytest
from pathlib import Path
from backend.app.services.bm25_retriever import BM25Retriever

SAMPLE_VERSES = [
    {"id": "DN 1:1", "pali": "evam me sutam", "english": "Thus have I heard"},
    {"id": "DN 1:2", "pali": "ekam samayam", "english": "At one time the Buddha"},
    {"id": "MN 10:1", "pali": "sammaditthi", "english": "right view right intention right speech"},
    {"id": "SN 22.59:1", "pali": "rupam aniccam", "english": "form is impermanent suffering not self"},
    {"id": "AN 1.1:1", "pali": "cittam dantam", "english": "the tamed mind brings happiness"},
]


def make_retriever():
    return BM25Retriever(SAMPLE_VERSES)


def test_retrieve_returns_list_of_dicts():
    results = make_retriever().retrieve("right view", top_k=3)
    assert isinstance(results, list)
    assert all(isinstance(x, dict) for x in results)


def test_retrieve_result_has_required_fields():
    results = make_retriever().retrieve("right view", top_k=1)
    assert results[0].keys() >= {"id", "pali", "english", "bm25_score"}


def test_exact_match_ranks_first():
    results = make_retriever().retrieve("right view", top_k=5)
    assert results[0]["id"] == "MN 10:1"


def test_top_k_limits_results():
    results = make_retriever().retrieve("Buddha", top_k=2)
    assert len(results) <= 2


def test_no_match_returns_empty():
    results = make_retriever().retrieve("zzzyyyxxxqqq", top_k=5)
    assert results == []


def test_scores_are_floats():
    results = make_retriever().retrieve("impermanent", top_k=3)
    assert all(isinstance(x["bm25_score"], float) for x in results)


def test_results_sorted_descending():
    results = make_retriever().retrieve("right view intention speech", top_k=5)
    scores = [x["bm25_score"] for x in results]
    assert scores == sorted(scores, reverse=True)


def test_from_directory(tmp_path):
    data = {
        "sutta_id": "MN10",
        "verses": [
            {"number": 1, "pali": "Majjhima Nikaya", "english": "Middle Discourses"},
            {"number": 2, "pali": "Satipatthana", "english": "Mindfulness Meditation"},
            {"number": 3, "pali": "evam me sutam", "english": "Thus have I heard at one time"},
        ],
    }
    (tmp_path / "mn10.json").write_text(json.dumps(data))
    r = BM25Retriever.from_directory(tmp_path)
    results = r.retrieve("mindfulness meditation", top_k=3)
    assert len(results) > 0
    assert results[0]["id"].startswith("MN")


def test_from_directory_raises_on_empty_dir(tmp_path):
    with pytest.raises(ValueError, match="No verses found"):
        BM25Retriever.from_directory(tmp_path)


def test_empty_verses_raises_value_error():
    with pytest.raises(ValueError, match="requires at least one verse"):
        BM25Retriever([])


SAMPLE_VERSES_WITH_NIKAYA = [
    {"id": "DN 1:1", "nikaya": "DN", "pali": "evam me sutam", "english": "Thus have I heard"},
    {"id": "MN 10:1", "nikaya": "MN", "pali": "sammaditthi", "english": "right view right intention"},
    {"id": "SN 22.59:1", "nikaya": "SN", "pali": "rupam aniccam", "english": "form is impermanent"},
    {"id": "AN 1.1:1", "nikaya": "AN", "pali": "cittam dantam", "english": "mind brings happiness"},
]


def test_nikaya_filter_restricts_to_requested_nikaya():
    r = BM25Retriever(SAMPLE_VERSES_WITH_NIKAYA)
    results = r.retrieve("right view", top_k=10, nikayas=["MN"])
    assert results and all(v["nikaya"] == "MN" for v in results)


def test_nikaya_filter_multiple_nikayas():
    r = BM25Retriever(SAMPLE_VERSES_WITH_NIKAYA)
    results = r.retrieve("right view impermanent", top_k=10, nikayas=["MN", "SN"])
    assert {v["nikaya"] for v in results} <= {"MN", "SN"}


def test_nikaya_filter_none_is_unfiltered():
    r = BM25Retriever(SAMPLE_VERSES_WITH_NIKAYA)
    unfiltered = r.retrieve("right view impermanent happiness", top_k=10)
    with_none = r.retrieve("right view impermanent happiness", top_k=10, nikayas=None)
    assert len(unfiltered) == len(with_none)


SAMPLE_VERSES_WITH_COMMENTARY = [
    {"id": "DN 1:1", "pali": "evam me sutam", "english": "Thus have I heard the Blessed One was dwelling"},
    {
        "id": "DN 1:2",
        "pali": "",
        "english": "This sutta introduces the Buddha as a teacher of devas",
        "section": "commentary",
    },
    {"id": "MN 10:1", "pali": "sati", "english": "Right mindfulness of breathing in the present moment"},
    {"id": "SN 22.59:1", "pali": "anicca", "english": "Form is impermanent suffering and not self"},
]


def test_exclude_commentary_drops_commentary_verses():
    r = BM25Retriever(SAMPLE_VERSES_WITH_COMMENTARY)
    results = r.retrieve("Thus have I heard sutta introduces Buddha", top_k=10, exclude_commentary=True)
    assert [v["id"] for v in results] == ["DN 1:1"]


def test_default_retrieve_still_returns_commentary():
    r = BM25Retriever(SAMPLE_VERSES_WITH_COMMENTARY)
    results = r.retrieve("Thus have I heard sutta introduces Buddha", top_k=10)
    assert {v["id"] for v in results} == {"DN 1:1", "DN 1:2"}
