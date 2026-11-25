from fastapi import APIRouter, status

from app.modules.chat.dependencies import ChatServiceDep
from app.modules.chat.schemas import AssistantResponse, ChatRequest

chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("", response_model=AssistantResponse, status_code=status.HTTP_200_OK)
async def chat(data: ChatRequest, service: ChatServiceDep) -> AssistantResponse:
    return await service.reply(data.content)


@chat_router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(service: ChatServiceDep) -> None:
    await service.end_session()