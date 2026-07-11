import re
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models


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
            chunks.append({
                "id": f"{formatted_id}:{verse_num}",
                "nikaya": nikaya,
                "pali": verse.get("pali", ""),
                "english": verse.get("english", "")
            })
        return chunks


_MODEL_CACHE: dict[str, TextEmbedding] = {}


class EmbeddingManager:
    """
    Handles the multilingual embedding model and Qdrant collection setup.
    Uses fastembed (ONNX Runtime) for compatibility with older CPUs.

    NOTE: the heavy TextEmbedding model is cached globally so that tests (and
    multiple pipeline instances) do not reload it for every SearchPipeline().
    """
    def __init__(self, model_name: str = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'):
        if model_name not in _MODEL_CACHE:
            _MODEL_CACHE[model_name] = TextEmbedding(model_name)
        self._model = _MODEL_CACHE[model_name]
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
