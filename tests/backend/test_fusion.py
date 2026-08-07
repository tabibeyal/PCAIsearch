from backend.app.services.fusion import rrf_fuse_multi

LIST_A = [
    {"id": "A", "english": "alpha"},
    {"id": "B", "english": "beta"},
    {"id": "C", "english": "gamma"},
]
LIST_B = [
    {"id": "B", "english": "beta"},
    {"id": "D", "english": "delta"},
]
LIST_C = [
    {"id": "A", "english": "alpha"},
    {"id": "E", "english": "epsilon"},
]


def test_rrf_fuse_multi_output_is_list_of_dicts():
    result = rrf_fuse_multi([LIST_A, LIST_B])
    assert isinstance(result, list)
    assert all(isinstance(x, dict) for x in result)


def test_rrf_fuse_multi_fusion_score_field_present():
    result = rrf_fuse_multi([LIST_A, LIST_B])
    assert all("fusion_score" in x for x in result)


def test_rrf_fuse_multi_all_ids_present():
    result = rrf_fuse_multi([LIST_A, LIST_B])
    ids = {x["id"] for x in result}
    assert ids == {"A", "B", "C", "D"}


def test_rrf_fuse_multi_item_in_both_lists_scores_higher_than_item_in_one():
    result = rrf_fuse_multi([LIST_A, LIST_B])
    scores = {x["id"]: x["fusion_score"] for x in result}
    # B appears in both LIST_A (rank 1) and LIST_B (rank 0) — should beat C (only LIST_A rank 2)
    assert scores["B"] > scores["C"]


def test_rrf_fuse_multi_later_list_item_not_penalised_vs_first_seen():
    """An item only in the second list at rank 0 should beat an item in the first list at rank 2."""
    result = rrf_fuse_multi([LIST_A, LIST_B])
    scores = {x["id"]: x["fusion_score"] for x in result}
    # D is rank 0 in LIST_B; C is rank 2 in LIST_A
    # D score = 1/61; C score = 1/63  →  D > C
    assert scores["D"] > scores["C"]


def test_rrf_fuse_multi_sorted_descending():
    result = rrf_fuse_multi([LIST_A, LIST_B, LIST_C])
    scores = [x["fusion_score"] for x in result]
    assert scores == sorted(scores, reverse=True)


def test_rrf_fuse_multi_three_lists_accumulates_correctly():
    # A is rank 0 in LIST_A and rank 0 in LIST_C → score = 1/61 + 1/61 = 2/61
    result = rrf_fuse_multi([LIST_A, LIST_B, LIST_C])
    scores = {x["id"]: x["fusion_score"] for x in result}
    expected_a = 1 / 61 + 1 / 61  # rank 0 in LIST_A, rank 0 in LIST_C
    assert abs(scores["A"] - expected_a) < 1e-9


def test_rrf_fuse_multi_accumulates_across_differing_ranks():
    # A at rank 0 in the first list, rank 2 in the second, with k=60:
    # score = 1/(60+0+1) + 1/(60+2+1) = 1/61 + 1/63
    first = [{"id": "A", "english": "alpha"}]
    second = [{"id": "B", "english": "beta"}, {"id": "C", "english": "gamma"}, {"id": "A", "english": "alpha"}]
    result = rrf_fuse_multi([first, second], k=60)
    score_a = next(x["fusion_score"] for x in result if x["id"] == "A")
    assert abs(score_a - (1 / 61 + 1 / 63)) < 1e-9


def test_rrf_fuse_multi_single_list_preserves_its_order():
    result = rrf_fuse_multi([LIST_A])
    assert [x["id"] for x in result] == [x["id"] for x in LIST_A]


def test_rrf_fuse_multi_empty_first_list_keeps_the_populated_one():
    result = rrf_fuse_multi([[], LIST_A])
    assert len(result) == len(LIST_A)


def test_rrf_fuse_multi_empty_second_list_keeps_the_populated_one():
    result = rrf_fuse_multi([LIST_A, []])
    assert len(result) == len(LIST_A)


def test_rrf_fuse_multi_empty_lists():
    assert rrf_fuse_multi([]) == []
    assert rrf_fuse_multi([[]]) == []
    assert rrf_fuse_multi([[], []]) == []


def test_rrf_fuse_multi_first_occurrence_payload_wins():
    """When the same ID appears in multiple lists, payload from first list is used."""
    list1 = [{"id": "X", "english": "from list1"}]
    list2 = [{"id": "X", "english": "from list2"}]
    result = rrf_fuse_multi([list1, list2])
    assert result[0]["english"] == "from list1"


def test_rrf_fuse_multi_custom_k_changes_scores():
    scores_k60 = {x["id"]: x["fusion_score"] for x in rrf_fuse_multi([LIST_A, LIST_B], k=60)}
    scores_k1 = {x["id"]: x["fusion_score"] for x in rrf_fuse_multi([LIST_A, LIST_B], k=1)}
    assert scores_k60 != scores_k1
