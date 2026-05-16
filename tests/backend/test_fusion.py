from backend.app.services.fusion import rrf_fuse, rrf_fuse_multi

DENSE = [
    {"id": "A", "english": "alpha", "score": 0.9},
    {"id": "B", "english": "beta", "score": 0.8},
    {"id": "C", "english": "gamma", "score": 0.7},
]
SPARSE = [
    {"id": "C", "english": "gamma", "bm25_score": 5.0},
    {"id": "D", "english": "delta", "bm25_score": 4.0},
    {"id": "A", "english": "alpha", "bm25_score": 3.0},
]


def test_output_is_list_of_dicts():
    result = rrf_fuse(DENSE, SPARSE)
    assert isinstance(result, list)
    assert all(isinstance(x, dict) for x in result)


def test_fusion_score_field_present():
    result = rrf_fuse(DENSE, SPARSE)
    assert all("fusion_score" in x for x in result)


def test_all_ids_present():
    result = rrf_fuse(DENSE, SPARSE)
    ids = {x["id"] for x in result}
    assert ids == {"A", "B", "C", "D"}


def test_item_in_both_lists_scores_higher():
    result = rrf_fuse(DENSE, SPARSE)
    scores = {x["id"]: x["fusion_score"] for x in result}
    # A appears in both lists (rank 0 dense, rank 2 sparse)
    # B only in dense (rank 1)
    assert scores["A"] > scores["B"]
    # C appears in both lists (rank 2 dense, rank 0 sparse)
    # D only in sparse (rank 1)
    assert scores["C"] > scores["D"]


def test_sorted_descending_by_fusion_score():
    result = rrf_fuse(DENSE, SPARSE)
    scores = [x["fusion_score"] for x in result]
    assert scores == sorted(scores, reverse=True)


def test_empty_dense():
    result = rrf_fuse([], SPARSE)
    assert len(result) == len(SPARSE)


def test_empty_sparse():
    result = rrf_fuse(DENSE, [])
    assert len(result) == len(DENSE)


def test_both_empty():
    result = rrf_fuse([], [])
    assert result == []


def test_custom_k_changes_scores():
    scores_k60 = {x["id"]: x["fusion_score"] for x in rrf_fuse(DENSE, SPARSE, k=60)}
    scores_k1 = {x["id"]: x["fusion_score"] for x in rrf_fuse(DENSE, SPARSE, k=1)}
    assert scores_k60 != scores_k1


def test_dense_payload_used_for_shared_ids():
    dense = [{"id": "X", "english": "from dense", "score": 0.9}]
    sparse = [{"id": "X", "english": "from sparse", "bm25_score": 5.0}]
    result = rrf_fuse(dense, sparse)
    assert result[0]["english"] == "from dense"


def test_fusion_score_correct_value():
    # A at rank 0 in dense, rank 2 in sparse with k=60:
    # score = 1/(60+0+1) + 1/(60+2+1) = 1/61 + 1/63
    dense = [{"id": "A", "english": "alpha"}]
    sparse = [{"id": "B", "english": "beta"}, {"id": "C", "english": "gamma"}, {"id": "A", "english": "alpha"}]
    result = rrf_fuse(dense, sparse, k=60)
    score_a = next(x["fusion_score"] for x in result if x["id"] == "A")
    expected = 1/61 + 1/63
    assert abs(score_a - expected) < 1e-9


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


def test_rrf_fuse_multi_single_list_matches_one_side_of_rrf_fuse():
    result_multi = rrf_fuse_multi([LIST_A])
    result_rrf = rrf_fuse(LIST_A, [])
    scores_multi = {x["id"]: x["fusion_score"] for x in result_multi}
    scores_rrf = {x["id"]: x["fusion_score"] for x in result_rrf}
    assert scores_multi == scores_rrf


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
