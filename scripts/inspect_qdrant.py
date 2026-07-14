"""Read-only inspection of the pali_canon Qdrant collection.

Reports point count and whether payloads carry the `section` commentary
marker (#101/#105). Prints no secrets — only collection metadata.
"""
import os
from qdrant_client import QdrantClient

COLLECTION = "pali_canon"

client = QdrantClient(
    url=os.environ.get("QDRANT_URL", "http://localhost:6333"),
    api_key=os.environ.get("QDRANT_API_KEY"),
    timeout=60,
)

try:
    info = client.get_collection(COLLECTION)
    print(f"collection: {COLLECTION}")
    print(f"points_count: {info.points_count}")
except Exception as e:
    print(f"get_collection error: {e!r}")
    raise SystemExit(1)

# Scroll a small sample to inspect payloads for the `section` marker.
sample = client.scroll(
    collection_name=COLLECTION,
    limit=10,
    with_payload=True,
    with_vectors=False,
)[0]
print(f"\nsample payloads ({len(sample)}):")
for r in sample:
    p = r.payload or {}
    print(
        f"  id={p.get('id')!r} nikaya={p.get('nikaya')!r} "
        f"section={p.get('section')!r} english={ (p.get('english') or '')[:50]!r}"
    )

# Count commentary-tagged points (must_not empty → match all with section=commentary).
# Total point count (unfiltered — no payload index needed).
try:
    total = client.count(COLLECTION, exact=True).count
    print(f"\ntotal points: {total}")
except Exception as e:
    print(f"\ntotal count error: {e!r}")

# Commentary tally via scroll: a filtered `count` 400s on the free tier
# ("Index required for section"), so count `section: commentary` payloads
# in Python while scrolling the whole collection.
commentary = 0
scrolled = 0
try:
    offset = None
    while True:
        rows, offset = client.scroll(
            collection_name=COLLECTION, limit=1000, offset=offset,
            with_payload=True, with_vectors=False,
        )
        for r in rows:
            if (r.payload or {}).get("section") == "commentary":
                commentary += 1
            scrolled += 1
        if offset is None:
            break
    print(f"scrolled: {scrolled}")
    print(f"commentary-tagged points: {commentary}")
except Exception as e:
    print(f"scroll tally error: {e!r}")