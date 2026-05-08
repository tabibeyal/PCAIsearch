import re
from typing import List
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models


class SuttaParser:
    """
    Parses SuttaCentral style raw data into canonical chunks.
    """
    def parse(self, data: dict) -> list:
        sutta_id = data.get("sutta_id", "Unknown")

        # Clean sutta_id for canonical format (e.g., "DN1" -> "DN 1")
        match = re.match(r"([a-zA-Z]+)(\d+)", sutta_id)
        if match:
            formatted_id = f"{match.group(1)} {match.group(2)}"
        else:
            formatted_id = sutta_id

        chunks = []
        for verse in data.get("verses", []):
            verse_num = verse.get("number")
            chunks.append({
                "id": f"{formatted_id}:{verse_num}",
                "pali": verse.get("pali", ""),
                "english": verse.get("english", "")
            })
        return chunks

class EmbeddingManager:
    """
    Handles the multilingual embedding model and Qdrant collection setup.
    """
    def __init__(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        # Load model once to be reused
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_embedding_dimension()

    def encode(self, text: str) -> list:
        """
        Encodes text into a vector.
        """
        embedding = self.model.encode(text)
        return embedding.tolist()

    def setup_collection(self, client: QdrantClient, collection_name: str, recreate: bool = False):
        """
        Creates a Qdrant collection if it does not exist.
        Pass recreate=True only for a full re-index — this drops all existing data.
        """
        if client.collection_exists(collection_name):
            if not recreate:
                print(f"Collection {collection_name} already exists, skipping creation.")
                return
            client.delete_collection(collection_name)
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=self.dimension,
                distance=models.Distance.COSINE
            )
        )
        print(f"Collection {collection_name} created with dimension {self.dimension}")
