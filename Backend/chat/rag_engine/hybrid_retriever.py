import asyncio

from chat.rag_engine.dense_retriever import retrieve_dense
from chat.rag_engine.bm25_retriever import retrieve_sparse
from chat.rag_engine.reranker import rerank_results

def reciprocal_rank_fusion(
    dense_results,
    sparse_results,
    k: int = 60,
):
    """
    Reciprocal Rank Fusion (RRF)

    Combines rankings from dense and sparse retrieval.
    """

    scores = {}

    for rank, doc in enumerate(dense_results):

        key = (
            doc["source"],
            doc["page"],
            doc["text"],
        )

        scores[key] = scores.get(key, 0) + (
            1 / (k + rank + 1)
        )

    for rank, doc in enumerate(sparse_results):

        key = (
            doc["source"],
            doc["page"],
            doc["text"],
        )

        scores[key] = scores.get(key, 0) + (
            1 / (k + rank + 1)
        )

    return scores


async def hybrid_retrieve(
    query: str,
    limit: int = 10,
):
    """
    Hybrid Retrieval

    1. Dense Retrieval (Qdrant)
    2. Sparse Retrieval (BM25)
    3. Reciprocal Rank Fusion
    """

    dense_results, sparse_results = await asyncio.gather(
        retrieve_dense(query, limit=limit),
        asyncio.to_thread(retrieve_sparse, query, limit),
    )

    rrf_scores = reciprocal_rank_fusion(
        dense_results,
        sparse_results,
    )

    all_docs = {}

    for doc in dense_results + sparse_results:

        key = (
            doc["source"],
            doc["page"],
            doc["text"],
        )

        all_docs[key] = doc

    ranked = sorted(
        rrf_scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    results = []

    for key, score in ranked[:limit]:

        doc = all_docs[key].copy()

        doc["rrf_score"] = score

        results.append(doc)

    reranked = await asyncio.to_thread(
        rerank_results,
        query,
        results,
        5,
    )
    return reranked