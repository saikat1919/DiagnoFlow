from fastapi import APIRouter, status, File, UploadFile, Form
from app.modules.chat.dependencies import ChatServiceDep
from app.core.exceptions.errors import ValidationError
from app.modules.chat.images import image_data_url
from app.modules.chat.schemas import AssistantResponse, ChatRequest

chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("", response_model=AssistantResponse, status_code=status.HTTP_200_OK)
async def chat(data: ChatRequest, service: ChatServiceDep) -> AssistantResponse:
    return await service.reply(data.content)

@chat_router.post("/image", response_model=AssistantResponse, status_code=status.HTTP_200_OK)
async def chat_with_image(
    service: ChatServiceDep,
    file: UploadFile = File(...),
    content: str = Form(""),
) -> AssistantResponse:
    if len(content) > 2000:
        raise ValidationError("Question must be at most 2000 characters")
    image_url = image_data_url(await file.read())
    return await service.reply_with_image(content, image_url)

@chat_router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(service: ChatServiceDep) -> None:
    await service.end_session()