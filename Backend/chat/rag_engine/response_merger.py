import asyncio

from chat.rag_engine.decision_layer import decide_context
from chat.services.generator import (
    generate_general_response,
    generate_hybrid_response,
)


async def get_response(
    query: str
):

    decision = await decide_context(query)

    mode = decision["mode"]
    contexts = decision["contexts"]

    if mode == "llm_only":
        answer = await asyncio.to_thread(
            generate_general_response, query
        )
    else:
        context_text = "\n\n".join(
            ctx["text"]
            for ctx in contexts
            if ctx["text"]
        )

        answer = await asyncio.to_thread(
            generate_hybrid_response, query, context_text
        )

    return {
        "answer": answer,
        "mode": mode,
        "sources": [
            {
                "source": ctx["source"],
                "page": ctx["page"],
                "score": ctx.get("rerank_score", ctx["score"]),
            }
            for ctx in contexts
        ] if mode == "hybrid_rag" else [],
    }