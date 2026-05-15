from typing import Any, Dict, List


def rrf_fuse(
    dense: List[Dict[str, Any]],
    sparse: List[Dict[str, Any]],
    k: int = 60,
) -> List[Dict[str, Any]]:
    """Reciprocal Rank Fusion over two ranked result lists keyed by 'id'."""
    scores: Dict[str, float] = {}
    sources: Dict[str, Dict[str, Any]] = {}

    for rank, item in enumerate(dense):
        item_id = item["id"]
        scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
        sources[item_id] = item

    for rank, item in enumerate(sparse):
        item_id = item["id"]
        scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
        if item_id not in sources:
            sources[item_id] = item

    return [
        {**sources[item_id], "fusion_score": score}
        for item_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
    ]
