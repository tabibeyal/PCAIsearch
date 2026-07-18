import re
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models

from backend.app.core.model_cache import get_cached_model


class SuttaParser:
    """
    Parses Thanissaro Bhikkhu JSON dumps into canonical chunks.
    """
    def parse(self, data: dict) -> list:
        sutta_id = data.get("sutta_id", "Unknown")

        # Clean sutta_id for canonical format (e.g., "DN1" -> "DN 1", "AN1.1" -> "AN 1.1")
        match = re.match(r"([a-zA-Z]+)([\d.]+)", sutta_id)
        if match:
            formatted_id = f"{match.group(1)} {match.group(2)}"
        else:
            formatted_id = sutta_id

        nikaya = formatted_id.split()[0].upper() if " " in formatted_id else formatted_id.upper()

        chunks = []
        for verse in data.get("verses", []):
            verse_num = verse.get("number")
            chunk = {
                "id": f"{formatted_id}:{verse_num}",
                "nikaya": nikaya,
                "pali": verse.get("pali", ""),
                "english": verse.get("english", ""),
            }
            # Translator-commentary marker from the fetch step (#101). Absent
            # on canon verses, so pre-marker dumps parse as all-canon.
            section = verse.get("section")
            if section:
                chunk["section"] = section
            chunks.append(chunk)
        return chunks


class EmbeddingManager:
    """
    Handles the multilingual embedding model and Qdrant collection setup.
    Uses fastembed (ONNX Runtime) for compatibility with older CPUs.
    """
    def __init__(self, model_name: str = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'):
        # Cached: this model is large and slow to load; without it, tests instantiating
        # many EmbeddingManagers would reload it and exhaust memory.
        self._model = get_cached_model("embedding", model_name, lambda: TextEmbedding(model_name))
        self.dimension = 384  # paraphrase-multilingual-MiniLM-L12-v2 output dim

    def encode(self, text: str) -> list:
        return next(iter(self._model.embed([text]))).tolist()

    def encode_batch(self, texts: list[str]) -> list[list]:
        return [v.tolist() for v in self._model.embed(texts)]

    def setup_collection(self, client: QdrantClient, collection_name: str, recreate: bool = False):
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
