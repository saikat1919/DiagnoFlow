import os
import sys
import uuid
import anyio
from mcp.server.stdio import stdio_server
from app.core.exceptions.errors import AppError
from app.db.session import SessionLocal
from app.mcp.context import MCP_USER
from app.mcp.server import server
from app.modules.patients.repositories import PatientRepository
from app.modules.users.models import Role, User
from app.modules.users.repositories import UserRepository
from app.modules.users.services import UserService


def _token_from_env() -> str | None:
    for name in ("DIAGNOFLOW_MCP_TOKEN", "MCP_ACCESS_TOKEN", "MCP_TOKEN"):
        value = os.environ.get(name)
        if value:
            return value.removeprefix("Bearer ").strip() or None
    return None


def _anonymous_user() -> User:
    return User(
        id=uuid.uuid4(),
        first_name="stdio",
        last_name="stdio",
        mobile_number="00000000000",
        email=None,
        password="",
        role=Role.PATIENT,
        patient_id=None,
        is_active=True,
    )


async def _serve() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


async def main() -> None:
    token = _token_from_env()
    if token is not None:
        async with SessionLocal() as session:
            try:
                user = await UserService(
                    UserRepository(session), PatientRepository(session)
                ).get_user_by_token(token)
            except AppError as exc:
                print(f"stdio: invalid or expired MCP token: {exc}", file=sys.stderr)
                raise SystemExit(2) from exc
            _ = (user.role, user.patient_id)
            await session.commit()
            reset = MCP_USER.set(user)
            try:
                await _serve()
            finally:
                MCP_USER.reset(reset)
        return

    print(
        "stdio: no DIAGNOFLOW_MCP_TOKEN set; running with search-only patient tools",
        file=sys.stderr,
    )
    reset = MCP_USER.set(_anonymous_user())
    try:
        await _serve()
    finally:
        MCP_USER.reset(reset)


if __name__ == "__main__":
    anyio.run(main)