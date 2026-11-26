from functools import lru_cache
from typing import Annotated
from fastapi import Depends
from app.core.config import get_settings
from app.integrations.embeddings.client import EmbeddingClient

@lru_cache
def get_embedding_client() -> EmbeddingClient:
    settings = get_settings()

    return EmbeddingClient(
        api_key=settings.GEMINI_API_KEY.get_secret_value()
    )

EmbeddingDep = Annotated[
    EmbeddingClient,
    Depends(get_embedding_client),
]
