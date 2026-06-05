from embeddings.embedding_model import get_embedding_model


def generate_embedding(text: str) -> list[float]:
    """
    Generate embedding for a single text.
    """

    model = get_embedding_model()

    embedding = model.encode(text)

    return embedding.tolist()


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for multiple texts.
    """

    model = get_embedding_model()

    embeddings = model.encode(texts)

    return embeddings.tolist()
