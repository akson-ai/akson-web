from typing import Generator

import gradio as gr

from agent import Agent


def create(agent: Agent) -> gr.Blocks:
    def respond(prompt: str, history: list[dict[str, str]]) -> Generator[list[dict[str, str]], None, None]:
        user_message = {"role": "user", "content": prompt}
        yield history + [user_message]
        reply = agent.message(prompt, session_id="gradio")
        assistant_message = {"role": "assistant", "content": reply}
        yield history + [user_message, assistant_message]

    with gr.Blocks() as demo:
        gr.Markdown(f"<h1 style='text-align: center; margin-bottom: 1rem'>{agent.name}</h1>")
        gr.Markdown(f"<p style='text-align: center'>{agent.description}</p>")
        chatbot = gr.Chatbot(type="messages")
        prompt = gr.Textbox(max_lines=1, label="Input", placeholder=f"Reply to {agent.name}...", autofocus=True)
        prompt.submit(respond, [prompt, chatbot], [chatbot])
        prompt.submit(lambda: "", None, [prompt])
        return demo
