import logging
import uuid
from collections.abc import Callable
from pathlib import Path
from app.core.exceptions.errors import NotFoundError
from app.integrations.embeddings.client import EmbeddingClient
from app.modules.medicines.models import Medicine
from app.modules.diagnostic_test_catalogue.models import TestCatalogue
from app.modules.knowledge.models import KnowledgeChunk
from app.modules.knowledge.repositories import KnowledgeRepository
from app.modules.knowledge.schemas import (
    ChunkCreate,
    ChunkPage,
    ChunkRead,
    ChunkUpdate,
    IngestResult,
    SearchHit,
    SearchMode,
    Source,
)

logger = logging.getLogger("uvicorn.error")

RRF_K = 60

POLICIES_FILE = Path(__file__).resolve().parents[3] / "scripts" / "data" / "policies.md"


def log_top(label: str, results: list[tuple[KnowledgeChunk, float]]) -> None:
    for i, (chunk, score) in enumerate(results[:3], start=1):
        logger.info(
            f"[search]   {label}  #{i}  score={float(score):.4f}  {chunk.title}"
        )


def to_hit(chunk: KnowledgeChunk, score: float) -> SearchHit:
    return SearchHit(
        source=chunk.source,
        title=chunk.title,
        content=chunk.content,
        score=round(float(score), 4),
    )


def to_read(chunk: KnowledgeChunk) -> ChunkRead:
    return ChunkRead.model_validate(chunk)


def fuse(
    *ranked_lists: list[tuple[KnowledgeChunk, float]],
) -> list[tuple[KnowledgeChunk, float]]:
    chunks: dict = {}
    scores: dict = {}
    for ranked in ranked_lists:
        for rank, (chunk, _) in enumerate(ranked, start=1):
            chunks[chunk.id] = chunk
            scores[chunk.id] = scores.get(chunk.id, 0) + 1 / (RRF_K + rank)
    best = sorted(scores, key=scores.get, reverse=True)
    return [(chunks[i], scores[i]) for i in best]


def policy_sections(text: str) -> list[tuple[str, str]]:
    sections = []
    for block in text.split("\n## ")[1:]:
        title, _, body = block.partition("\n")
        sections.append((title.strip(), body.strip()))
    return sections


def medicine_text(m: Medicine) -> str:
    description = m.description or ""
    return (
        f"{m.brand_name} {m.generic_name} {m.strength} {m.dosage_form.value}. "
        f"{description} Price: {m.selling_price} BDT. "
        f"Reorder level: {m.reorder_level}."
    )


def test_text(t: TestCatalogue) -> str:
    department = t.department.name if t.department is not None else ""
    return (
        f"{t.test_code} {t.test_name}. Department: {department}. "
        f"Price: {t.price} BDT. Expected delivery: {t.expected_delivery_time}."
    )


class KnowledgeService:
    def __init__(self, repo: KnowledgeRepository, embedder: EmbeddingClient) -> None:
        self.repo = repo
        self.embedder = embedder

    async def search(
        self, query: str, mode: SearchMode, source: Source | None, limit: int
    ) -> list[SearchHit]:
        src = source.value if source else None
        logger.info(f'[search] mode={mode.value} source={src or "all"} query="{query}"')

        if mode == SearchMode.KEYWORD:
            results = await self.repo.keyword_search(query, src, limit)
            log_top("keyword", results)
        elif mode == SearchMode.SEMANTIC:
            vector = await self.embedder.embed_query(query)
            results = await self.repo.semantic_search(vector, src, limit)
            log_top("semantic", results)
        else:
            vector = await self.embedder.embed_query(query)
            keyword = await self.repo.keyword_search(query, src, limit * 2)
            log_top("keyword", keyword)
            semantic = await self.repo.semantic_search(vector, src, limit * 2)
            log_top("semantic", semantic)
            results = fuse(keyword, semantic)[:limit]
            log_top("fused (RRF)", results)

        return [to_hit(chunk, score) for chunk, score in results]

    async def create_chunk(self, data: ChunkCreate) -> ChunkRead:
        vector = await self.embedder.embed_document(data.title, data.content)
        chunk = await self.repo.add(
            KnowledgeChunk(
                source=data.source.value,
                title=data.title,
                content=data.content,
                embedding=vector,
            )
        )
        return to_read(chunk)

    async def _get_or_404(self, chunk_id: uuid.UUID) -> KnowledgeChunk:
        chunk = await self.repo.get(chunk_id)
        if chunk is None:
            raise NotFoundError("Knowledge chunk", str(chunk_id))
        return chunk

    async def get_chunk(self, chunk_id: uuid.UUID) -> ChunkRead:
        return to_read(await self._get_or_404(chunk_id))

    async def list_chunks(
        self, source: Source | None, page: int, page_size: int
    ) -> ChunkPage:
        src = source.value if source else None
        items, total = await self.repo.list_chunks(src, page, page_size)
        return ChunkPage(
            items=[to_read(c) for c in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update_chunk(self, chunk_id: uuid.UUID, data: ChunkUpdate) -> ChunkRead:
        chunk = await self._get_or_404(chunk_id)
        changes = {
            field: value
            for field, value in data.model_dump(exclude_unset=True).items()
            if value is not None and value != getattr(chunk, field)
        }
        for field, value in changes.items():
            setattr(chunk, field, value)
        if changes:
            chunk.embedding = await self.embedder.embed_document(
                chunk.title, chunk.content
            )
        await self.repo.save(chunk)
        return to_read(chunk)

    async def delete_chunk(self, chunk_id: uuid.UUID) -> None:
        await self.repo.delete(await self._get_or_404(chunk_id))

    async def ingest_all(
        self, on_item: Callable[[str, str], None] | None = None
    ) -> IngestResult:
        chunks: list[KnowledgeChunk] = []

        async def embed(source: Source, title: str, content: str) -> None:
            if on_item:
                on_item(source.value, title)
            vector = await self.embedder.embed_document(title, content)
            chunks.append(
                KnowledgeChunk(
                    source=source.value,
                    title=title,
                    content=content,
                    embedding=vector,
                )
            )

        if POLICIES_FILE.exists():
            sections = policy_sections(POLICIES_FILE.read_text(encoding="utf-8"))
        else:
            logger.warning("[ingest] no policies file at %s; skipping policies", POLICIES_FILE)
            sections = []
        for title, body in sections:
            await embed(Source.POLICY, title, body)

        medicines = await self.repo.active_medicines()
        for m in medicines:
            await embed(Source.MEDICINE, f"{m.brand_name} {m.strength}", medicine_text(m))

        tests = await self.repo.active_tests()
        for t in tests:
            await embed(Source.TEST, f"{t.test_code} {t.test_name}", test_text(t))

        await self.repo.replace_sources(
            chunks, [Source.POLICY.value, Source.MEDICINE.value, Source.TEST.value]
        )
        return IngestResult(
            policies=len(sections),
            medicines=len(medicines),
            tests=len(tests),
            total=len(chunks),
        )