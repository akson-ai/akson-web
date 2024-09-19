import gradio as gr
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

import registry
import openai_compat
import chat_interface
from loader import load_agents


load_dotenv()

agents = load_agents()

app = FastAPI()

openai_compat.setup_routes(app, agents)

for agent in agents.values():
    registry.register(agent)
    gr.mount_gradio_app(app, chat_interface.create(agent), f"/chat/{agent.name}")


@app.get("/", response_class=HTMLResponse)
async def index():
    return f"""
    <html>
        <head>
            <title>Crowd</title>
        </head>
        <body>
            <h1>Agents</h1>
            <ul>
            {"".join([f"<li><a href='/chat/{agent}'>{agent}</a></li>" for agent in sorted(agents.keys())])}
            </ul>
        </body>
    </html>
    """
