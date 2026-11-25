import uuid
from fastapi import APIRouter, Query, status
from app.modules.knowledge.dependencies import KnowledgeServiceDep
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
from app.modules.users.dependencies import AdminDep, CurrentUserDep

knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])

@knowledge_router.get("/search", response_model=list[SearchHit])
async def search(
    service: KnowledgeServiceDep,
    user: CurrentUserDep,
    q: str = Query(min_length=2, max_length=200),
    mode: SearchMode = SearchMode.HYBRID,
    source: Source | None = None,
    limit: int = Query(default=3, ge=1, le=10),
) -> list[SearchHit]:
    return await service.search(q, mode, source, limit)

@knowledge_router.post("/ingest", response_model=IngestResult)
async def ingest(service: KnowledgeServiceDep, admin: AdminDep) -> IngestResult:
    return await service.ingest_all()

@knowledge_router.post("", response_model=ChunkRead, status_code=status.HTTP_201_CREATED)
async def create_chunk(data: ChunkCreate, service: KnowledgeServiceDep, admin: AdminDep) -> ChunkRead:
    return await service.create_chunk(data)

@knowledge_router.get("", response_model=ChunkPage)
async def list_chunks(
    service: KnowledgeServiceDep,
    admin: AdminDep,
    source: Source | None = None,
    page: int = 1,
    page_size: int = 10,
) -> list[ChunkRead]:
    return await service.list_chunks(source, page, page_size)

@knowledge_router.get("/{chunk_id}", response_model=ChunkRead)
async def get_chunk(chunk_id: uuid.UUID, service: KnowledgeServiceDep, admin: AdminDep) -> ChunkRead:
    return await service.get_chunk(chunk_id)

@knowledge_router.put("/{chunk_id}", response_model=ChunkRead)
async def update_chunk(chunk_id: uuid.UUID, data: ChunkUpdate, service: KnowledgeServiceDep, admin: AdminDep) -> ChunkRead:
    return await service.update_chunk(chunk_id, data)

@knowledge_router.delete("/{chunk_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chunk(chunk_id: uuid.UUID, service: KnowledgeServiceDep, admin: AdminDep) -> None:
    await service.delete_chunk(chunk_id)