import random

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing_extensions import Literal

from agent import Agent


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)


class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: str


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: list[Choice]
    usage: Usage


def setup_routes(app: FastAPI, agents: dict[str, Agent]):
    async def chat_completions(request: ChatCompletionRequest):
        try:
            agent = agents[request.model]
        except KeyError:
            raise HTTPException(status_code=404, detail="Agent not found")

        # TODO call completion api
        content = agent.message(request.messages[-1].content, sender="Human", session_id=None)
        assert isinstance(content, str)

        completion_tokens = len(content.split())
        prompt_tokens = sum(len(msg.content.split()) for msg in request.messages)

        return ChatCompletionResponse(
            id=f"chatcmpl-{random.randint(1000000, 9999999)}",
            object="chat.completion",
            created=int(random.random() * 1000000000),
            model=request.model,
            choices=[Choice(index=0, message=Message(role="assistant", content=content), finish_reason="stop")],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )

    app.add_api_route("/v1/chat/completions", chat_completions, methods=["POST"], response_model=ChatCompletionResponse)
