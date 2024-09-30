import gradio as gr

from agent import Agent


def create(agent: Agent) -> gr.ChatInterface:
    def handle_message(message: str, history: list[tuple[str, str]]) -> str:
        return agent.message(message, session_id="gradio")

    return gr.ChatInterface(
        handle_message, title=agent.name, description=agent.description, retry_btn=None, undo_btn=None, clear_btn=None
    )
