
from chat.rag_engine.hybrid_retriever import hybrid_retrieve

from utils.config import settings


async def decide_context(
    query: str
):
    """
    Decide whether to use:
    - Retrieved context
    - Hybrid mode
    - Pure LLM
    """

    contexts = await hybrid_retrieve(query)

    if not contexts:
        return {
            "mode": "llm_only",
            "contexts": []
        }

    best_score = contexts[0]["rerank_score"]

    if best_score >= settings.HYBRID_RAG_THRESHOLD:
        mode = "hybrid_rag"

    else:
        mode = "llm_only"

    return {
        "mode": mode,
        "contexts": contexts
    }