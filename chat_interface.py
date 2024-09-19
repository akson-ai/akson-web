import gradio as gr

from agent import Agent


def create(agent: Agent) -> gr.ChatInterface:
    def handle_message(message: str, _, request: gr.Request):
        return agent.message(message, sender="Human", session_id=request.session_hash)

    return gr.ChatInterface(
        handle_message, title=agent.name, description=agent.description, retry_btn=None, undo_btn=None, clear_btn=None
    )
