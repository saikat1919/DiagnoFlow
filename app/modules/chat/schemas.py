from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

class AssistantResponse(BaseModel):
    reply: str
    tool_calls: list[str] = []