from qdrant_client import QdrantClient
from shared.config import settings

_client = None


def get_qdrant_client() -> QdrantClient:
    global _client

    if _client is None:
        _client = QdrantClient(
            url=settings.QDRANT_URL
        )

    return _client