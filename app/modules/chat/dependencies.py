import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated
from fastapi import Depends
from app.core.exceptions.errors import UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import SessionDep
from app.integrations.llm.dependencies import LLMDep
from app.integrations.llm.base import LLMProvider
from app.modules.chat.history import ChatHistoryStore
from app.modules.chat.services import ChatService
from app.modules.chat.summaries import SummaryRepository
from app.modules.knowledge.dependencies import KnowledgeServiceDep
from app.modules.users.dependencies import UserServiceDep, oauth2_scheme
from app.modules.users.models import User


@dataclass
class ChatSession:
    user: User
    session_key: str
    expires_at: datetime


async def get_chat_session(
    token: Annotated[str, Depends(oauth2_scheme)],
    service: UserServiceDep,
) -> ChatSession:
    payload = decode_access_token(token)
    if payload is None or "exp" not in payload:
        raise UnauthorizedError("Invalid or expired token")
    user = await service.get_user_by_token(token)
    return ChatSession(
        user=user,
        session_key=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
    )


ChatSessionDep = Annotated[ChatSession, Depends(get_chat_session)]


@lru_cache
def get_chat_history_store() -> ChatHistoryStore:
    return ChatHistoryStore()


HistoryStoreDep = Annotated[ChatHistoryStore, Depends(get_chat_history_store)]


def get_summary_repository(session: SessionDep) -> SummaryRepository:
    return SummaryRepository(session)


SummaryRepositoryDep = Annotated[SummaryRepository, Depends(get_summary_repository)]


def get_chat_service(
    llm: LLMDep,
    knowledge: KnowledgeServiceDep,
    summaries: SummaryRepositoryDep,
    history: HistoryStoreDep,
    session: ChatSessionDep,
) -> ChatService:
    return ChatService(
        llm=llm,
        knowledge=knowledge,
        summaries=summaries,
        history=history,
        user=session.user,
        session_key=session.session_key,
        expires_at=session.expires_at,
    )


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]