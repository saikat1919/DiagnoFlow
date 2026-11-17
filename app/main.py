from fastapi import FastAPI, Depends
from sqlalchemy import text
from app.core.config import Settings, get_settings
from app.db.session import SessionDep

app = FastAPI(title=get_settings().APP_NAME)

@app.get("/health")
async def health_check(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME}

@app.get("/db/health")
async def db_healthcheck(session: SessionDep) -> dict[str, str]:
    result = await session.execute(text("SELECT version();"))
    ext = await session.execute(text(text="SELECT extname FROM pg_extension WHERE extname = 'vector';"))
    has_vector = ext.scalar_one_or_none() is not None
    return {
        "database": "connected",
        "version": result.scalar_one(),
        "has_vector_db": "yes" if has_vector else "no",
    }