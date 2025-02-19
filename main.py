import json
import uuid
from collections import defaultdict

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse

import registry
from framework import Assistant, Chat
from loader import load_assistants
from logger import logger

load_dotenv()

assistants = load_assistants()

for name, assistant in assistants.items():
    registry.register(name, assistant)

chats = defaultdict(Chat)

app = FastAPI()


@app.get("/")
async def index():
    """Redirect to the chat app."""
    return RedirectResponse(f"/chat?id={uuid.uuid4()}")


@app.get("/chat")
async def get_chat_app():
    """Serve the chat web app."""
    return FileResponse("web/chat.html")


@app.get("/assistants")
async def get_assistants():
    """Return a list of available assistants."""
    return list({"name": name} for name in assistants.keys())


@app.get("/history/{chat_id}")
async def get_history(chat_id: str):
    """Return the history of a chat session."""
    chat = chats[chat_id]
    history = []
    for message in chat.messages:
        if message["role"] in ["user", "assistant"]:
            history.append({"role": message["role"], "content": message["content"]})
    return history


class ClientMessage(BaseModel):
    content: str
    assistant: str
    chat_id: str


@app.post("/message")
async def handle_message(params: ClientMessage, request: Request):
    """Handle a message from the client."""
    logger.info("Received message: %s", params)

    chat = chats[params.chat_id]
    chat.messages.append({"role": "user", "content": params.content})

    selected_assistant = assistants[params.assistant]
    assert isinstance(selected_assistant, Assistant)

    # TODO assistant returns a single message, handle multiple
    message = selected_assistant.run(chat)
    await chat.queue.put({"control": "new_message"})

    for chunk in message:
        await chat.queue.put({"chunk": chunk})
        if await request.is_disconnected():
            logger.info("Client disconnected, stopping streaming")
            break


@app.get("/events/{chat_id}")
async def stream_events(chat_id: str):
    """Stream events to the client."""

    async def generate_events():
        chat = chats[chat_id]
        while True:
            message = await chat.queue.get()
            yield ServerSentEvent(json.dumps(message))

    return EventSourceResponse(generate_events())


# Must be mounted after above handlers
app.mount("/", StaticFiles(directory="web/static"))
