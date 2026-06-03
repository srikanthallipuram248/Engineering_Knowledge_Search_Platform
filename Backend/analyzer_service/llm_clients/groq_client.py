from functools import lru_cache

from langchain_groq import ChatGroq

from shared.config import settings


@lru_cache(maxsize=1)
def get_llm() -> ChatGroq:
    """Return a cached LangChain ChatGroq instance."""
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_ANALYSIS_MODEL,
        temperature=0,
        max_tokens=4096,
    )
