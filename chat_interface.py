import gradio as gr

from agent import Agent


def create(agent: Agent) -> gr.ChatInterface:
    def handle_message(message: str, history: list[tuple[str, str]]) -> str:
        messages = []
        for human, assistant in history:
            if human:
                messages.append({"role": "user", "content": human})
            if assistant:
                messages.append({"role": "assistant", "content": assistant})

        messages.append({"role": "user", "content": message})
        return agent.complete(messages)

    return gr.ChatInterface(
        handle_message, title=agent.name, description=agent.description, retry_btn=None, undo_btn=None, clear_btn=None
    )
