import pytest
from backend.app.services.sutta_title_index import SuttaTitleIndex


SAMPLE_ENTRIES = [
    {"sutta_id": "MN10", "title_pali": "Satipaṭṭhānasutta", "title_english": "Mindfulness Meditation"},
    {"sutta_id": "DN22", "title_pali": "Mahāsatipaṭṭhānasutta", "title_english": "The Longer Discourse on Mindfulness Meditation"},
    {"sutta_id": "MN117", "title_pali": "Mahācattārīsakasutta", "title_english": "The Great Forty"},
    {"sutta_id": "SN22.59", "title_pali": "Anattalakkhaṇasutta", "title_english": "The Characteristic of Non-Self"},
    {"sutta_id": "MN26", "title_pali": "Ariyapariyesanāsutta", "title_english": "The Noble Search"},
    {"sutta_id": "SN56.11", "title_pali": "Dhammacakkappavattanasutta", "title_english": "Setting the Wheel of the Dhamma in Motion"},
]


def make_index(entries=None):
    return SuttaTitleIndex(entries or SAMPLE_ENTRIES)


def test_finds_mn10_for_mindfulness_query():
    index = make_index()
    results = index.search("four foundations of mindfulness", top_n=3)
    sutta_ids = [r[0] for r in results]
    assert "MN10" in sutta_ids


def test_finds_dn22_for_longer_mindfulness_query():
    index = make_index()
    results = index.search("longer discourse mindfulness meditation", top_n=3)
    sutta_ids = [r[0] for r in results]
    assert "DN22" in sutta_ids


def test_finds_sn5611_for_wheel_dhamma_query():
    index = make_index()
    results = index.search("setting wheel of the dhamma in motion first sermon", top_n=3)
    sutta_ids = [r[0] for r in results]
    assert "SN56.11" in sutta_ids


def test_returns_scores_as_floats():
    index = make_index()
    results = index.search("mindfulness meditation", top_n=3)
    assert all(isinstance(score, float) for _, score in results)


def test_returns_at_most_top_n():
    index = make_index()
    results = index.search("mindfulness", top_n=2)
    assert len(results) <= 2


def test_returns_empty_for_no_matching_terms():
    index = make_index()
    results = index.search("zzzzquantum blockchain xyz", top_n=3)
    assert results == []


def test_results_sorted_descending_by_score():
    index = make_index()
    results = index.search("mindfulness meditation discourse", top_n=5)
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)


def test_loads_from_dumps_directory(tmp_path):
    import json
    suttas = [
        ("mn10.json", "MN10", "Satipaṭṭhānasutta", "Mindfulness Meditation"),
        ("mn117.json", "MN117", "Mahācattārīsakasutta", "The Great Forty"),
        ("sn2259.json", "SN22.59", "Anattalakkhaṇasutta", "The Characteristic of Non-Self"),
        ("mn26.json", "MN26", "Ariyapariyesanāsutta", "The Noble Search"),
        ("sn5611.json", "SN56.11", "Dhammacakkappavattanasutta", "Setting the Wheel of the Dhamma in Motion"),
    ]
    for filename, sutta_id, pali_title, eng_title in suttas:
        (tmp_path / filename).write_text(json.dumps({
            "sutta_id": sutta_id,
            "verses": [
                {"number": 1, "pali": f"Nikāya", "english": f"Discourses"},
                {"number": 2, "pali": pali_title, "english": eng_title},
            ]
        }))

    index = SuttaTitleIndex.from_directory(tmp_path)
    results = index.search("mindfulness meditation", top_n=3)
    assert results[0][0] == "MN10"
