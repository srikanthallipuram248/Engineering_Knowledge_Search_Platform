import httpx

from qdrant_client import QdrantClient

from utils.config import settings


client = QdrantClient(
    url=settings.QDRANT_URL
)


async def get_query_embedding(
    query: str
) -> list[float]:

    timeout = httpx.Timeout(settings.EMBEDDING_REQUEST_TIMEOUT)

    async with httpx.AsyncClient(timeout=timeout) as http_client:
        response = await http_client.post(
            f"{settings.AI_PIPELINE_URL}/api/v1/embed/",
            json={"text": query},
        )

        response.raise_for_status()

        return response.json()["embedding"]


async def retrieve_dense(
    query: str,
    limit: int = 5
):
    """
    Retrieve top matching chunks from Qdrant.
    """

    query_embedding = await get_query_embedding(
        query
    )

    results = client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=query_embedding,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    contexts = []

    for hit in results:

        contexts.append(
            {
                "score": hit.score,
                "text": hit.payload.get("text"),
                "source": hit.payload.get("source"),
                "page": hit.payload.get("page"),
            }
        )

    return contexts