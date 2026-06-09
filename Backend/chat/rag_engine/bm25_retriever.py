from rank_bm25 import BM25Okapi
from qdrant_client import QdrantClient

from utils.config import settings


client = QdrantClient(
    url=settings.QDRANT_URL
)

_cache: dict | None = None


def _scroll_documents() -> list[dict]:
    documents = []
    offset = None

    while True:
        points, offset = client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        for point in points:
            payload = point.payload
            documents.append(
                {
                    "text": payload.get("text", ""),
                    "source": payload.get("source"),
                    "page": payload.get("page"),
                }
            )

        if offset is None:
            break

    return documents


def _build_cache() -> dict:
    documents = _scroll_documents()

    if not documents:
        return {"documents": [], "bm25": None}

    corpus = [doc["text"].split() for doc in documents]

    return {
        "documents": documents,
        "bm25": BM25Okapi(corpus),
    }


def warm_bm25_cache() -> None:
    """Load documents from Qdrant and build the BM25 index."""
    global _cache
    _cache = _build_cache()


def refresh_bm25_cache() -> None:
    """Rebuild the BM25 cache after new documents are ingested."""
    warm_bm25_cache()


def retrieve_sparse(
    query: str,
    limit: int = 5,
) -> list[dict]:
    """
    BM25 retrieval using an in-memory cached index.
    """
    global _cache

    if _cache is None:
        warm_bm25_cache()

    documents = _cache["documents"]
    bm25 = _cache["bm25"]

    if not documents or bm25 is None:
        return []

    scores = bm25.get_scores(query.split())

    ranked = sorted(
        zip(documents, scores),
        key=lambda x: x[1],
        reverse=True,
    )

    results = []

    for doc, score in ranked[:limit]:
        results.append(
            {
                "score": float(score),
                "text": doc["text"],
                "source": doc["source"],
                "page": doc["page"],
            }
        )

    return results
