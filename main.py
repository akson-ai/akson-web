import json
import uuid

from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse
from starlette.requests import ClientDisconnect

import registry
from framework import Assistant, Chat, ChatState
from loader import load_assistants
from logger import logger

load_dotenv()

assistants = load_assistants()
# TODO find a way to make default assistant configurable
default_assistant = "assistant"

for name, assistant in assistants.items():
    registry.register(name, assistant)


# Need to keep a single instance of each chat in memory in order to do pub/sub on queue
# TODO try streaming response
chats: dict[str, Chat] = {}


def _get_chat_state(chat_id: str) -> ChatState:
    try:
        return ChatState.load_from_disk(chat_id)
    except FileNotFoundError:
        return ChatState.create_new(chat_id, default_assistant)


def _get_chat(chat_id: str) -> Chat:
    try:
        return chats[chat_id]
    except KeyError:
        state = _get_chat_state(chat_id)
        chat = Chat(state)
        chats[chat_id] = chat
        return chat


app = FastAPI()


@app.get("/", include_in_schema=False)
async def index():
    """Redirect to the chat app."""
    return RedirectResponse(f"/chat")


@app.get("/chat", include_in_schema=False)
async def get_chat_app(id: str | None = None):
    """Serve the chat web app."""
    if not id:
        return RedirectResponse(f"/chat?id={uuid.uuid4()}")
    return FileResponse("web/chat.html")


class AssistantModel(BaseModel):
    name: str

    class Config:
        title = "Assistant"


@app.get("/assistants", response_model=list[AssistantModel])
async def get_assistants():
    """Return a list of available assistants."""
    return list(AssistantModel(name=name) for name in sorted(assistants.keys()))


@app.get("/{chat_id}/state", response_model=ChatState)
async def get_chat_state(state: ChatState = Depends(_get_chat_state)):
    """Return the state of a chat session."""
    return state


@app.put("/{chat_id}/assistant")
async def set_assistant(assistant: str = Body(...), chat: Chat = Depends(_get_chat)):
    """Update the assistant for a chat session."""
    chat.state.assistant = assistant
    chat.state.save_to_disk()


class MessageRequest(BaseModel):
    content: str = Body(...)
    assistant: str = Body(...)


def _get_assistant(message: MessageRequest) -> Assistant:
    return assistants[message.assistant]


@app.post("/{chat_id}/message")
async def send_message(
    request: Request,
    message: MessageRequest,
    assistant: Assistant = Depends(_get_assistant),
    chat: Chat = Depends(_get_chat),
):
    """Handle a message from the client."""
    chat.state.messages.append({"role": "user", "content": message.content})

    chat._request = request
    try:
        if message.content.strip() == "/clear":
            chat.state.messages.clear()
            chat.state.save_to_disk()
            logger.info("Chat cleared")
            await chat._send_control("clear")
            return
        await assistant.run(chat)
    except ClientDisconnect:
        # TODO save interrupted messages
        logger.info("Client disconnected")
    finally:
        chat._request = None
        chat.state.save_to_disk()


@app.get("/{chat_id}/events")
async def get_events(chat: Chat = Depends(_get_chat)):
    """Stream events to the client over SSE."""

    async def generate_events():
        while True:
            message = await chat._queue.get()
            yield ServerSentEvent(json.dumps(message))

    return EventSourceResponse(generate_events())


# Must be mounted after above handlers
app.mount("/", StaticFiles(directory="web/static"))
