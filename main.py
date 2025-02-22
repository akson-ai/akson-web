import json
import uuid

from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse
from starlette.requests import ClientDisconnect

import registry
from framework import Assistant, PersistentChat
from loader import load_assistants
from logger import logger

load_dotenv()

assistants = load_assistants()

for name, assistant in assistants.items():
    registry.register(name, assistant)


# Need to keep a single instance of each chat in memory in order to do pub/sub on queue
chats: dict[str, PersistentChat] = {}


def get_chat(chat_id: str) -> PersistentChat:
    try:
        chat = chats[chat_id]
    except KeyError:
        chat = PersistentChat(chat_id)
        try:
            chat.load()
        except FileNotFoundError:
            pass

        chats[chat_id] = chat

    return chat


app = FastAPI()


@app.get("/", include_in_schema=False)
async def index():
    """Redirect to the chat app."""
    return RedirectResponse(f"/chat?id={uuid.uuid4()}")


@app.get("/chat", include_in_schema=False)
async def get_chat_app():
    """Serve the chat web app."""
    return FileResponse("web/chat.html")


@app.get("/assistants")
async def get_assistants():
    """Return a list of available assistants."""
    return list({"name": name} for name in sorted(assistants.keys()))


# TODO save all chat state, not only messages
@app.get("/{chat_id}/history")
async def get_history(chat: PersistentChat = Depends(get_chat)):
    """Return the history of a chat session."""
    history = []
    for message in chat.messages:
        if message["role"] in ["user", "assistant"]:
            history.append({"role": message["role"], "content": message["content"]})
    return history


def get_assistant(name: str = Body(alias="assistant")) -> Assistant:
    return assistants[name]


@app.post("/{chat_id}/message")
async def handle_message(
    request: Request,
    content: str = Body(...),
    assistant: Assistant = Depends(get_assistant),
    chat: PersistentChat = Depends(get_chat),
):
    """Handle a message from the client."""
    if content.strip() == "/clear":
        chat.messages.clear()
        chat.save()
        logger.info("Chat cleared")
        await chat._send_control("clear")
        return

    chat.messages.append({"role": "user", "content": content})

    chat._request = request
    try:
        await assistant.run(chat)
    except ClientDisconnect:
        # TODO save half messages
        logger.info("Client disconnected")
    finally:
        chat._request = None
        chat.save()


@app.get("/{chat_id}/events")
async def stream_events(chat: PersistentChat = Depends(get_chat)):
    """Stream events to the client."""

    async def generate_events():
        while True:
            message = await chat._queue.get()
            yield ServerSentEvent(json.dumps(message))

    return EventSourceResponse(generate_events())


# Must be mounted after above handlers
app.mount("/", StaticFiles(directory="web/static"))
