import logging
import time
import math
from google import genai
from google.genai import types

logger = logging.getLogger("uvicorn.error")

EMBEDDING_DIM = 768
EMBEDDING_MODEL = "gemini-embedding-001"


class EmbeddingClient:
    def __init__(self, api_key: str) -> None:
        self.client = genai.Client(api_key=api_key)

    async def _embed(
        self,
        text: str,
        task_type: str,
    ) -> list[float]:
        preview = text[:80].replace("\n", " ")
        dots = "..." if len(text) > 80 else ""

        logger.info(
            f"[embedding] -> model: '{preview}{dots}'"
        )

        started = time.perf_counter()

        response = await self.client.aio.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=EMBEDDING_DIM,
            ),
        )

        vector = response.embeddings[0].values
        norm = math.sqrt(sum(value * value for value in vector))

        if norm == 0:
            raise ValueError("Gemini returned a zero embedding vector")

        vector = [value / norm for value in vector]

        if len(vector) != EMBEDDING_DIM:
            raise ValueError(
                f"Expected {EMBEDDING_DIM} dimensions, "
                f"received {len(vector)}"
            )

        ms = (time.perf_counter() - started) * 1000

        first = ", ".join(
            str(round(n, 4)) for n in vector[:5]
        )

        logger.info(
            f"[embedding] <- model returned "
            f"{len(vector)} numbers: [{first}, ...] "
            f"in {ms:.0f} ms"
        )

        return vector

    async def embed(self, text: str) -> list[float]:
        return await self._embed(
            text,
            task_type="RETRIEVAL_DOCUMENT",
        )

    async def embed_query(self, question: str) -> list[float]:
        return await self._embed(
            question,
            task_type="RETRIEVAL_QUERY",
        )

    async def embed_document(
        self,
        title: str,
        text: str,
    ) -> list[float]:
        document = f"title: {title}\ntext: {text}"

        return await self._embed(
            document,
            task_type="RETRIEVAL_DOCUMENT",
        )
