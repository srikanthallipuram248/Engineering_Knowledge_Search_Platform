from functools import lru_cache

from sentence_transformers import CrossEncoder


@lru_cache(maxsize=1)
def get_reranker():

    return CrossEncoder(
        "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )


def rerank_results(
    query: str,
    documents: list,
    top_k: int = 5,
):
    """
    Re-rank retrieved documents using a cross encoder.
    """

    if not documents:
        return []

    reranker = get_reranker()

    pairs = [
        (query, doc["text"])
        for doc in documents
    ]

    scores = reranker.predict(pairs)

    for doc, score in zip(documents, scores):

        doc["rerank_score"] = float(score)

    documents.sort(
        key=lambda x: x["rerank_score"],
        reverse=True,
    )

    return documents[:top_k]