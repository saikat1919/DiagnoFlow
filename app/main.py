from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy import text
from app.core.config import Settings, get_settings
from app.db.session import SessionDep
import app.db.all_models
from app.api.v1.router import api_router
from app.core.exceptions.handlers import register_exception_handlers
from app.mcp.server import mcp_asgi_app, session_manager


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with session_manager.run():
        yield
app = FastAPI(title=get_settings().APP_NAME, lifespan=lifespan)

register_exception_handlers(app)
app.include_router(router=api_router)
app.add_route("/mcp", mcp_asgi_app)


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