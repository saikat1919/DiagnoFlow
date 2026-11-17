from sqlalchemy.ext.asyncio import (create_async_engine,
                                    async_sessionmaker,
                                    AsyncEngine,
                                    AsyncSession)
from fastapi import Depends
from typing import Annotated, AsyncIterator
from app.core.config import get_settings


settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={"server_settings": {"search_path": f"{settings.DB_SCHEMA}, public"}}
)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

SessionDep = Annotated[
    AsyncSession, Depends(dependency=get_session, scope="function")
]

StreamingSessionDep = Annotated[AsyncSession, Depends(dependency=get_session)]