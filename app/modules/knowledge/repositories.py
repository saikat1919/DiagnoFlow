import uuid
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.medicines.models import Medicine
from app.modules.diagnostic_test_catalogue.models import TestCatalogue
from app.modules.knowledge.models import KnowledgeChunk


class KnowledgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db_session = session

    async def replace_sources(self, chunks: list[KnowledgeChunk], sources: list[str]) -> None:
        await self.db_session.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.source.in_(sources))
        )
        self.db_session.add_all(chunks)
        await self.db_session.flush()

    async def add(self, chunk: KnowledgeChunk) -> KnowledgeChunk:
        self.db_session.add(chunk)
        return await self.save(chunk)

    async def save(self, chunk: KnowledgeChunk) -> KnowledgeChunk:
        chunk.updated_at = func.now()
        await self.db_session.flush()
        await self.db_session.refresh(chunk)
        return chunk

    async def get(self, chunk_id: uuid.UUID) -> KnowledgeChunk | None:
        return await self.db_session.get(KnowledgeChunk, chunk_id)

    async def list_chunks(
        self, source: str | None, page: int, page_size: int
    ) -> tuple[list[KnowledgeChunk], int]:
        base = select(KnowledgeChunk)
        if source:
            base = base.where(KnowledgeChunk.source == source)
        total = await self.db_session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        stmt = (
            base.order_by(KnowledgeChunk.created_at.desc(), KnowledgeChunk.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.db_session.scalars(stmt)).all()
        return list(items), total or 0

    async def delete(self, chunk: KnowledgeChunk) -> None:
        await self.db_session.delete(chunk)
        await self.db_session.flush()

    async def active_medicines(self) -> list[Medicine]:
        stmt = select(Medicine).where(Medicine.is_active.is_(True))
        return list((await self.db_session.scalars(stmt)).all())

    async def active_tests(self) -> list[TestCatalogue]:
        stmt = select(TestCatalogue).where(TestCatalogue.is_active.is_(True))
        return list((await self.db_session.scalars(stmt)).all())

    async def keyword_search(
        self, query: str, source: str | None, limit: int
    ) -> list[tuple[KnowledgeChunk, float]]:
        document = func.to_tsvector(
            "english", KnowledgeChunk.title + " " + KnowledgeChunk.content
        )
        words = func.websearch_to_tsquery("english", query)
        score = func.ts_rank(document, words)
        stmt = (
            select(KnowledgeChunk, score)
            .where(document.op("@@")(words))
            .order_by(score.desc())
            .limit(limit)
        )
        if source:
            stmt = stmt.where(KnowledgeChunk.source == source)
        return [(chunk, s) for chunk, s in (await self.db_session.execute(stmt)).all()]

    async def semantic_search(
        self, vector: list[float], source: str | None, limit: int
    ) -> list[tuple[KnowledgeChunk, float]]:
        distance = KnowledgeChunk.embedding.cosine_distance(vector)
        stmt = select(KnowledgeChunk, 1 - distance).order_by(distance).limit(limit)
        if source:
            stmt = stmt.where(KnowledgeChunk.source == source)
        return [(chunk, s) for chunk, s in (await self.db_session.execute(stmt)).all()]