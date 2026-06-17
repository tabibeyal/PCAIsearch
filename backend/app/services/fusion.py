from typing import Any


def rrf_fuse_multi(
    lists: list[list[dict[str, Any]]],
    k: int = 60,
) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion over N ranked result lists keyed by 'id'.

    When the same ID appears in multiple lists, the payload from its first
    occurrence (across all lists in order) is used.
    """
    scores: dict[str, float] = {}
    sources: dict[str, dict[str, Any]] = {}

    for lst in lists:
        for rank, item in enumerate(lst):
            item_id = item["id"]
            if item_id is None:
                continue
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
            if item_id not in sources:
                sources[item_id] = item

    return [
        {**sources[item_id], "fusion_score": score}
        for item_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
    ]
