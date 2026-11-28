import json
from typing import Any
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import (
    StreamableHTTPASGIApp,
    StreamableHTTPSessionManager,
)
from mcp.shared.exceptions import MCPError
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from app.core.exceptions.errors import AppError
from app.db.session import SessionLocal
from app.integrations.embeddings.dependencies import get_embedding_client
from app.mcp.context import MCP_USER
from app.modules.chat.summaries import SummaryRepository
from app.modules.chat.tools import execute_tool, tools_for_role
from app.modules.knowledge.repositories import KnowledgeRepository
from app.modules.knowledge.services import KnowledgeService
from app.modules.patients.repositories import PatientRepository
from app.modules.users.repositories import UserRepository
from app.modules.users.services import UserService


class MCPAuthMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope["headers"]}
        auth = headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            await self._unauthorized(send)
            return
        try:
            async with SessionLocal() as session:
                user = await UserService(
                    UserRepository(session), PatientRepository(session)
                ).get_user_by_token(auth[7:])
        except AppError:
            await self._unauthorized(send)
            return
        reset = MCP_USER.set(user)
        try:
            await self.app(scope, receive, send)
        finally:
            MCP_USER.reset(reset)

    async def _unauthorized(self, send: Send) -> None:
        body = b'{"detail": "Authentication required"}'
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


async def list_tools(ctx, params) -> types.ListToolsResult:
    user = MCP_USER.get()
    if user is None:
        return types.ListToolsResult(tools=[])
    tools = [
        types.Tool(
            name=spec.name,
            description=spec.description,
            input_schema=spec.parameters,
        )
        for spec in tools_for_role(user.role)
    ]
    return types.ListToolsResult(tools=tools)


async def call_tool(ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
    user = MCP_USER.get()
    if user is None:
        raise MCPError(-32001, "Authentication required")
    async with SessionLocal() as session:
        summaries = SummaryRepository(session)
        knowledge = KnowledgeService(
            KnowledgeRepository(session), get_embedding_client()
        )
        result: dict[str, Any] = await execute_tool(
            summaries, knowledge, user, params.name, params.arguments or {}
        )
    return types.CallToolResult(
        content=[
            types.TextContent(
                text=json.dumps(result, ensure_ascii=False, default=str)
            )
        ],
        is_error="error" in result,
    )


server = Server("diagnoflow", on_list_tools=list_tools, on_call_tool=call_tool)

session_manager = StreamableHTTPSessionManager(app=server)
mcp_asgi_app = MCPAuthMiddleware(StreamableHTTPASGIApp(session_manager))