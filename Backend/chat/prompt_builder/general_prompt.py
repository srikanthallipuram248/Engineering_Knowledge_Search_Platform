from langchain_core.prompts import ChatPromptTemplate


def build_general_prompt(query: str):
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are an engineering knowledge assistant.

Answer clearly and accurately.
If you do not know the answer, say so.
Do not hallucinate.
                """,
            ),
            ("human", "{query}"),
        ]
    )

    return prompt.invoke({"query": query})