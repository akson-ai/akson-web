import os
import importlib

import gradio as gr
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

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
    def handle_message(message, _):
        return agent.message("Human", message)

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
