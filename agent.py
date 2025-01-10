from abc import ABC, abstractmethod
from typing import Generator

from gradio.components import Image
from openai.types.chat import ChatCompletionMessageParam


class Agent(ABC):

    name: str
    """Name of the agent. Must be unique. Other agents use this name to refer to it."""

    description: str
    """Description of the agent. It tells what the agent can do. Used during planning."""

    messages: list[ChatCompletionMessageParam] = []
    """List of messages the agent has sent so far."""

    def __repr__(self):
        return f"Agent<{self.name}>"

    @abstractmethod
    def message(self, input: str, *, session_id: str | None) -> Generator[str | Image, None, None]:
        """Sends a message to the agent. Agents should remember previous messages."""
