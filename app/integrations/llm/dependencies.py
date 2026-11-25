from functools import lru_cache
from typing import Annotated
from fastapi import Depends
from app.core.config import get_settings
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.groq import GroqProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    return GroqProvider(
        api_key=settings.GROQ_API_KEY.get_secret_value(),
        base_url=settings.GROQ_BASE_URL,
        model=settings.GROQ_MODEL,
    )

LLMDep = Annotated[LLMProvider, Depends(get_llm_provider)]