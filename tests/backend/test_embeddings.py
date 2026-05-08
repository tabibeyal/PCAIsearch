import pytest
from backend.app.core.indexing import EmbeddingManager
from qdrant_client import QdrantClient
from qdrant_client.http import models

def test_embedding_generation():
    manager = EmbeddingManager()
    text = "The Noble Eightfold Path"
    embedding = manager.encode(text)

    assert isinstance(embedding, list)
    assert len(embedding) > 0
    # Check for expected dimension of MiniLM-L12 (384)
    assert len(embedding) == 384

def test_qdrant_collection_setup():
    # Use in-memory Qdrant for testing
    client = QdrantClient(":memory:")
    manager = EmbeddingManager()

    collection_name = "test_pali_canon"
    manager.setup_collection(client, collection_name)

    collections = client.get_collections()
    assert any(c.name == collection_name for c in collections.collections)
