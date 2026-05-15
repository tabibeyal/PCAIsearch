from backend.app.services.fusion import rrf_fuse

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
