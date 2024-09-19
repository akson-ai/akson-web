import os
import random
import importlib
from typing import Literal

import gradio as gr
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from agent import Agent
from logger import logger


load_dotenv()

agents = {}

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def index():
    return f"""
    <html>
        <head>
            <title>Crowd</title>
        </head>
        <body>
            <h1>Agents</h1>
            {"<br>\n".join([f"<a href='/chat/{agent.name}'>{agent.name}</a>" for agent in agents.values()])}
        </body>
    </html>
    """


def create_chat_interface(agent: Agent) -> gr.ChatInterface:
    def handle_message(message: str, _, request: gr.Request):
        return agent.message(message, sender="Human", session_id=request.session_hash)

    return gr.ChatInterface(
        handle_message, title=agent.name, description=agent.description, retry_btn=None, undo_btn=None, clear_btn=None
    )


agents_dir = os.path.join(os.path.dirname(__file__), "agents")
logger.info("Agents directory: %s", agents_dir)
for agent_file in os.listdir(agents_dir):
    agent_file = os.path.basename(agent_file)
    module_name, extension = os.path.splitext(agent_file)
    if extension != ".py":
        continue
    module_name = f"agents.{module_name}"
    logger.info("Loading file: %s", agent_file)
    module = importlib.import_module(module_name)
    agent = module.agent
    agents[agent.name] = agent
    if not isinstance(agent, Agent):
        continue
    logger.info("Agent loaded: %s", agent.name)
    interface = create_chat_interface(agent)
    gr.mount_gradio_app(app, interface, f"/chat/{agent.name}")


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


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    try:
        agent = agents[request.model]
    except KeyError:
        raise HTTPException(status_code=404, detail="Agent not found")

    content = agent.message("User", request.messages[-1].content)
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
