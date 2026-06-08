from langchain_core.prompts import ChatPromptTemplate


def build_rag_prompt(query: str, context: str):
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are an engineering knowledge assistant.

Use ONLY the provided context.

If the answer is not present in the context,
say that the information was not found.
                """,
            ),
            (
                "human",
                """
Context:
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