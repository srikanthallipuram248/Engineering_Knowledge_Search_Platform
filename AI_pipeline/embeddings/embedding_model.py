from sentence_transformers import SentenceTransformer
from shared.config import settings

_model = None


def get_embedding_model():
    global _model

    if _model is None:
        _model = SentenceTransformer(
            settings.EMBEDDING_MODEL
        )

    return _model
