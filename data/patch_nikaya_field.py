"""
One-time migration: add 'nikaya' payload field to all existing Qdrant points.
Derives the value from the existing 'id' field (e.g., 'DN 15:3' -> 'DN').
"""
import sys
from qdrant_client import QdrantClient
from qdrant_client.http import models

COLLECTION = "pali_canon"
BATCH_SIZE = 500


def patch(qdrant_url: str = "http://localhost:6333"):
    client = QdrantClient(url=qdrant_url)
    offset = None
    total = 0

    while True:
        results, offset = client.scroll(
            collection_name=COLLECTION,
            limit=BATCH_SIZE,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        if not results:
            break

        for point in results:
            sutta_id = point.payload.get("id", "")
            nikaya = sutta_id.split()[0].upper() if " " in sutta_id else sutta_id.split(":")[0].upper()
            client.set_payload(
                collection_name=COLLECTION,
                payload={"nikaya": nikaya},
                points=[point.id],
            )

        total += len(results)
        print(f"Patched {total} points...")

        if offset is None:
            break

    print(f"Done. {total} points updated with 'nikaya' field.")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:6333"
    patch(url)
