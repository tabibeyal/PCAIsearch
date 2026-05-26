import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient
from qdrant_client.http import models
from backend.app.core.indexing import SuttaParser, EmbeddingManager

def process_sutta_dumps(
    dump_dir: str,
    qdrant_url: str = os.environ.get("QDRANT_URL", "http://localhost:6333"),
):
    """
    Processes SuttaCentral JSON dumps and indexes them into Qdrant.
    """
    parser = SuttaParser()
    embedding_mgr = EmbeddingManager()
    client = QdrantClient(url=qdrant_url, api_key=os.environ.get("QDRANT_API_KEY"), timeout=60)

    collection_name = "pali_canon"
    embedding_mgr.setup_collection(client, collection_name)

    # Build set of already-indexed point IDs to allow resume after interruption
    indexed_ids: set = set()
    try:
        offset = None
        while True:
            results, offset = client.scroll(
                collection_name=collection_name,
                limit=1000,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
            for r in results:
                indexed_ids.add(str(r.id))
            if offset is None:
                break
        if indexed_ids:
            print(f"Resuming: {len(indexed_ids)} points already indexed, skipping those suttas.")
    except Exception:
        pass  # collection empty or doesn't exist yet

    # Process all JSON files in the dump directory
    for filename in sorted(os.listdir(dump_dir)):
        if not filename.endswith(".json"):
            continue

        file_path = os.path.join(dump_dir, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Error decoding JSON in {filename}, skipping.")
                continue

        suttas = data if isinstance(data, list) else [data]
        for sutta in suttas:
            chunks = parser.parse(sutta)
            if not chunks:
                continue

            # Skip if every chunk in this sutta is already indexed
            point_ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, c['id'])) for c in chunks]
            if indexed_ids and all(pid in indexed_ids for pid in point_ids):
                print(f"Skipping {filename} (already indexed).")
                continue

            print(f"Indexing {filename}...")
            texts = [f"{c['pali']} {c['english']}" for c in chunks]
            vectors = embedding_mgr.encode_batch(texts)

            points = [
                models.PointStruct(
                    id=pid,
                    vector=vec,
                    payload=chunk,
                )
                for pid, chunk, vec in zip(point_ids, chunks, vectors)
            ]
            batch_size = 100
            for i in range(0, len(points), batch_size):
                client.upsert(collection_name=collection_name, points=points[i:i + batch_size])
            indexed_ids.update(point_ids)

    print(f"Indexing complete. Collection {collection_name} is ready.")

if __name__ == "__main__":
    # Default to a 'data/dumps' directory
    DUMP_DIR = "data/dumps"
    if not os.path.exists(DUMP_DIR):
        os.makedirs(DUMP_DIR)
        print(f"Created {DUMP_DIR}. Please place SuttaCentral JSON dumps here.")
    else:
        process_sutta_dumps(DUMP_DIR)
