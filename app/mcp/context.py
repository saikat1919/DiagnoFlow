from contextvars import ContextVar
from app.modules.users.models import User

MCP_USER: ContextVar[User | None] = ContextVar("mcp_user", default=None)