from langchain_core.prompts import ChatPromptTemplate


def build_hybrid_prompt(
    query: str,
    context: str,
):
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are an engineering knowledge assistant.

Use the retrieved context as your PRIMARY source.

If the context is incomplete, you may supplement
the answer using your own engineering knowledge.

Clearly prioritize retrieved information over
general knowledge.
                """,
            ),
            (
                "human",
                """
Retrieved Context:
{context}

Question:
{query}
                """,
            ),
        ]
    )

    return prompt.invoke(
        {
            "query": query,
            "context": context,
        }
    )