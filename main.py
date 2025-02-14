import asyncio
import json
from textwrap import dedent
from typing import AsyncGenerator

import gradio as gr
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse

import chat_interface
import openai_compat
import registry
from loader import load_agents
from logger import logger

load_dotenv()

agents = load_agents()

app = FastAPI()

openai_compat.setup_routes(app, agents)

for agent in agents.values():
    registry.register(agent)
    gr.mount_gradio_app(app, chat_interface.create(agent), f"/agents/{agent.name}")


@app.get("/")
async def index():
    return RedirectResponse("/agents")


@app.get("/agents", response_class=HTMLResponse)
async def get_agents():
    return dedent(
        f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>Crowd</title>
                <link rel="stylesheet" href="/style.css">
            </head>
            <body>
                <h1>Agents</h1>
                <ul>
                {"".join([f"<li><a href='/agents/{agent.name}'>{agent.name}</a></li>" for agent in agents.values()])}
                </ul>
            </body>
        </html>
        """
    ).strip()


@app.get("/style.css")
async def styles():
    return FileResponse("style.css")


@app.get("/chat")
async def chat_app():
    return FileResponse("web/index.html")


message_queue = asyncio.Queue()
agent = agents["chatgpt"]


@app.get("/history")
async def get_history():
    return agent.history()


@app.post("/message")
async def handle_message(request: Request):
    data = await request.json()
    message = data.get("message")
    logger.info(f"Received message: {message}")
    response = agent.message(message)
    for message in response:
        await message_queue.put({"message": message})


@app.get("/events")
async def stream_events():
    async def generate_events() -> AsyncGenerator[ServerSentEvent, None]:
        while True:
            message = await message_queue.get()
            yield ServerSentEvent(json.dumps(message))

    return EventSourceResponse(generate_events())
