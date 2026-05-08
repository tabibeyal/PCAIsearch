import json
import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models
from backend.app.core.indexing import SuttaParser, EmbeddingManager

def process_sutta_dumps(dump_dir: str, qdrant_url: str = "http://localhost:6333"):
    """
    Processes SuttaCentral JSON dumps and indexes them into Qdrant.
    """
    parser = SuttaParser()
    embedding_mgr = EmbeddingManager()
    client = QdrantClient(url=qdrant_url)

    collection_name = "pali_canon"
    embedding_mgr.setup_collection(client, collection_name)

    # Process all JSON files in the dump directory
    for filename in os.listdir(dump_dir):
        if filename.endswith(".json"):
            file_path = os.path.join(dump_dir, filename)
            print(f"Processing {filename}...")

            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    # Handle both single-sutta and multi-sutta files
                    suttas = data if isinstance(data, list) else [data]

                    for sutta in suttas:
                        chunks = parser.parse(sutta)
                        if not chunks:
                            continue

                        texts = [f"{c['pali']} {c['english']}" for c in chunks]
                        vectors = embedding_mgr.model.encode(texts, show_progress_bar=False)

                        points = [
                            models.PointStruct(
                                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk['id'])),
                                vector=vec.tolist(),
                                payload=chunk,
                            )
                            for chunk, vec in zip(chunks, vectors)
                        ]
                        client.upsert(collection_name=collection_name, points=points)
                except json.JSONDecodeError:
                    print(f"Error decoding JSON in {filename}, skipping.")

    print(f"Indexing complete. Collection {collection_name} is ready.")

if __name__ == "__main__":
    # Default to a 'data/dumps' directory
    DUMP_DIR = "data/dumps"
    if not os.path.exists(DUMP_DIR):
        os.makedirs(DUMP_DIR)
        print(f"Created {DUMP_DIR}. Please place SuttaCentral JSON dumps here.")
    else:
        process_sutta_dumps(DUMP_DIR)
