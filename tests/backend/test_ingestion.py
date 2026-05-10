import pytest
from unittest.mock import MagicMock
from backend.app.core.indexing import SuttaParser, EmbeddingManager
from qdrant_client import QdrantClient
from qdrant_client.http import models

def test_ingestion_pipeline_full_flow():
    # 1. Setup
    parser = SuttaParser()
    embedding_mgr = EmbeddingManager()
    client = QdrantClient(":memory:")
    collection_name = "pali_canon"
    embedding_mgr.setup_collection(client, collection_name)

    raw_data = {
        "sutta_id": "DN1",
        "verses": [
            {"number": 1, "pali": "evam me sutaṃ", "english": "Thus have I heard"},
            {"number": 2, "pali": "tada", "english": "Then"}
        ]
    }

    # 2. Execution (The logic we are about to implement in process_dumps.py)
    chunks = parser.parse(raw_data)
    points = []
    for idx, chunk in enumerate(chunks):
        text_to_embed = f"{chunk['pali']} {chunk['english']}"
        vector = embedding_mgr.encode(text_to_embed)
        points.append(models.PointStruct(
            id=idx,
            vector=vector,
            payload=chunk
        ))

    client.upsert(collection_name=collection_name, points=points)

    # 3. Verification
    results = client.scroll(collection_name=collection_name)
    assert len(results[0]) == 2
    assert results[0][0].payload['id'] == "DN 1:1"
    assert results[0][0].payload['pali'] == "evam me sutaṃ"

def test_parser_formats_dotted_sutta_id():
    parser = SuttaParser()
    data = {
        "sutta_id": "AN1.1",
        "verses": [
            {"number": 1, "pali": "Evaṁ me sutaṁ", "english": "Thus have I heard"}
        ]
    }
    chunks = parser.parse(data)
    assert chunks[0]["id"] == "AN 1.1:1"
