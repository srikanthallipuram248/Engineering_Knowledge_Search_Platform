
from chat.rag_engine.retriever import retrieve_context

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

    contexts = await retrieve_context(query)

    if not contexts:
        return {
            "mode": "llm_only",
            "contexts": []
        }

    best_score = contexts[0]["score"]

    if best_score >= settings.RAG_HIGH_THRESHOLD:
        mode = "rag"

    elif best_score >= settings.RAG_LOW_THRESHOLD:
        mode = "hybrid"

    else:
        mode = "llm_only"

    return {
        "mode": mode,
        "contexts": contexts
    }