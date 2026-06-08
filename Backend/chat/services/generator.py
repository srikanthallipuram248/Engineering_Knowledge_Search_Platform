from analysis.llm_clients.groq_client import get_llm

from chat.prompt_builder.general_prompt import build_general_prompt
from chat.prompt_builder.hybrid_prompt import build_hybrid_prompt
from chat.prompt_builder.rag_prompt import build_rag_prompt

def generate_general_response(query: str) -> str:
    llm = get_llm()

    prompt = build_general_prompt(query)

    response = llm.invoke(prompt)

    return response.content


def generate_rag_response(
    query: str,
    context: str,
) -> str:
    llm = get_llm()

    prompt = build_rag_prompt(
        query,
        context,
    )

    response = llm.invoke(prompt)

    return response.content

def generate_hybrid_response(
    query: str,
    context: str,
) -> str:

    llm = get_llm()

    prompt = build_hybrid_prompt(
        query,
        context,
    )

    response = llm.invoke(prompt)

    return response.content