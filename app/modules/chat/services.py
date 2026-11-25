from datetime import UTC, datetime
from typing import Any
from app.integrations.llm.base import ChatMessage, LLMProvider
from app.modules.chat.history import ChatHistoryStore
from app.modules.chat.prompts import ASSISTANT_PROMPT
from app.modules.chat.schemas import AssistantResponse
from app.modules.chat.summaries import SummaryRepository
from app.modules.chat.tools import execute_tool, tools_for_role
from app.modules.knowledge.services import KnowledgeService
from app.modules.users.models import User


class ChatService:
    def __init__(
        self,
        llm: LLMProvider,
        knowledge: KnowledgeService,
        summaries: SummaryRepository,
        history: ChatHistoryStore,
        user: User,
        session_key: str,
        expires_at: datetime,
    ) -> None:
        self.llm = llm
        self.knowledge = knowledge
        self.summaries = summaries
        self.history = history
        self.user = user
        self.session_key = session_key
        self.expires_at = expires_at

    async def reply(self, content: str) -> AssistantResponse:
        now = datetime.now(UTC)
        system = ASSISTANT_PROMPT.replace("{role}", self.user.role.value)
        messages = await self.history.get(self.session_key, now)
        messages = [*messages, ChatMessage(role="user", content=content)]
        result = await self.llm.chat_with_tools(
            system=system,
            messages=messages,
            tools=tools_for_role(self.user.role),
            run_tool=self.run_tool,
        )
        await self.history.append(
            self.session_key, self.expires_at, now, content, result.text
        )
        return AssistantResponse(reply=result.text, tool_calls=result.tool_calls)

    async def run_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        return await execute_tool(self.summaries, self.knowledge, self.user, name, args)

    async def end_session(self) -> None:
        await self.history.clear(self.session_key)