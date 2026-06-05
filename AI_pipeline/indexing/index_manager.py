from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct
)
from shared.config import settings
from indexing.qdrant_client import get_qdrant_client
import uuid

COLLECTION_NAME = settings.QDRANT_COLLECTION
VECTOR_SIZE = 384

def string_to_uuid(s: str) -> str:
    """Convert any string to a deterministic UUID."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, s))

def create_collection():
    client = get_qdrant_client()

    existing = client.get_collections().collections

    names = [c.name for c in existing]

    if COLLECTION_NAME not in names:

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )

def store_embeddings(
    ids: list[str],
    embeddings: list[list[float]],
    payloads: list[dict]
):
    client = get_qdrant_client()

    points = []

    for i in range(len(ids)):
        points.append(
            PointStruct(
                id=string_to_uuid(ids[i]),
                vector=embeddings[i],
                payload=payloads[i]
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )

def search(
    query_embedding: list[float],
    limit: int = 5
):
    client = get_qdrant_client()

    return client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
