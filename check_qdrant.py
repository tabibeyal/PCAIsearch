import os
from qdrant_client import QdrantClient

url = os.environ.get("QDRANT_URL", "http://localhost:6333")
api_key = os.environ.get("QDRANT_API_KEY")

print(f"Connecting to: {url}")
print(f"Authenticated: {bool(api_key)}")
c = QdrantClient(url=url, api_key=api_key)
collections = c.get_collections().collections
if collections:
    for col in collections:
        info = c.get_collection(col.name)
        print(f"  {col.name}: {info.points_count} points")
else:
    print("No collections found — Qdrant is empty at this URL.")
