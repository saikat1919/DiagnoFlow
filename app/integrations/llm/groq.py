import json
import logging
from openai import AsyncOpenAI, APIError
from app.core.exceptions.errors import LLMUnavailableError
from app.integrations.llm.base import ChatMessage, LLMReply, ToolSpec, ToolRunner

MAX_TOOL_ROUNDS = 5

logger = logging.getLogger("uvicorn.error")

def to_openai_tools(tools: list[ToolSpec]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]

def describe_call(name: str, args: dict) -> str:
    return f"{name}({', '.join(f'{k}={v!r}' for k, v in args.items())})"

class GroqProvider:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def chat(self, system: str, messages: list[ChatMessage]) -> str:
        payload = [{"role": "system", "content": system}] + [
            {"role": m.role, "content": m.content} for m in messages
        ]
        try:
            response = await self.client.chat.completions.create(
                model=self.model, messages=payload
            )
        except APIError as exc:
            raise LLMUnavailableError(str(exc)) from exc
        return response.choices[0].message.content or ""

    async def chat_with_tools(
        self,
        system: str,
        messages: list[ChatMessage],
        tools: list[ToolSpec],
        run_tool: ToolRunner,
    ) -> LLMReply:
        payload: list[dict] = [{"role": "system", "content": system}] + [
            {"role": m.role, "content": m.content} for m in messages
        ]
        tool_calls: list[str] = []

        for round_no in range(1, MAX_TOOL_ROUNDS + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=payload,
                    tools=to_openai_tools(tools),
                )
            except APIError as exc:
                raise LLMUnavailableError(str(exc)) from exc

            message = response.choices[0].message
            calls = message.tool_calls or []
            if not calls:
                logger.info("[round %s] model answered with text", round_no)
                return LLMReply(text=message.content or "", tool_calls=tool_calls)

            payload.append(message.model_dump(exclude_none=True))
            for call in calls:
                args = json.loads(call.function.arguments or "{}")
                tool_calls.append(describe_call(call.function.name, args))
                logger.info("[round %s] model asked for %s", round_no, tool_calls[-1])
                result = await run_tool(call.function.name, args)
                payload.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )

        return LLMReply(
            text="Sorry, I couldn't finish that. Please ask in a simpler way.",
            tool_calls=tool_calls,
        )