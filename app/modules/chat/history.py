import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from app.integrations.llm.base import ChatMessage


@dataclass
class _SessionHistory:
    expires_at: datetime
    messages: list[ChatMessage] = field(default_factory=list)


class ChatHistoryStore:
    def __init__(self, max_messages: int = 20) -> None:
        self._sessions: dict[str, _SessionHistory] = {}
        self._lock = asyncio.Lock()
        self._max_messages = max_messages

    def _prune(self, now: datetime) -> None:
        expired = [key for key, entry in self._sessions.items() if now >= entry.expires_at]
        for key in expired:
            del self._sessions[key]

    async def get(self, session_key: str, now: datetime) -> list[ChatMessage]:
        async with self._lock:
            self._prune(now)
            entry = self._sessions.get(session_key)
            return list(entry.messages) if entry is not None else []

    async def append(
        self, session_key: str, expires_at: datetime, now: datetime,
        user_content: str, assistant_content: str,
    ) -> None:
        async with self._lock:
            self._prune(now)
            if now >= expires_at:
                return
            entry = self._sessions.get(session_key)
            if entry is None:
                entry = _SessionHistory(expires_at=expires_at)
                self._sessions[session_key] = entry
            entry.expires_at = expires_at
            entry.messages.append(ChatMessage(role="user", content=user_content))
            entry.messages.append(ChatMessage(role="assistant", content=assistant_content))
            entry.messages = entry.messages[-self._max_messages:]

    async def clear(self, session_key: str) -> None:
        async with self._lock:
            self._sessions.pop(session_key, None)