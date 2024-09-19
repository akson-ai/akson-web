from textwrap import dedent

import gradio as gr
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import Response, HTMLResponse, PlainTextResponse

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
    gr.mount_gradio_app(app, chat_interface.create(agent), f"/agents/{agent.name}")


@app.get("/", response_class=HTMLResponse)
async def index():
    return dedent(
        f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>Crowd</title>
                <link rel="stylesheet" href="/styles.css">
            </head>
            <body>
                <h1>Agents</h1>
                <ul>
                {"".join([f"<li><a href='/agents/{agent}'>{agent}</a></li>" for agent in sorted(agents.keys())])}
                </ul>
            </body>
        </html>
        """
    ).strip()


@app.get("/styles.css", response_class=PlainTextResponse)
async def get_css():
    css_content = """
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        ul {
            list-style-type: none;
            padding: 0;
        }
        li {
            background-color: #fff;
            margin-bottom: 10px;
            border-radius: 5px;
            overflow: hidden;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        a {
            display: block;
            padding: 15px 20px;
            color: #2980b9;
            text-decoration: none;
            transition: background-color 0.3s ease;
        }
        a:hover {
            background-color: #ecf0f1;
        }
    """
    return Response(content=css_content, media_type="text/css")
