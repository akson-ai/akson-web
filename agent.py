from abc import ABC, abstractmethod
from typing import Generator

from gradio.components import Image
from gradio.components.chatbot import MessageDict


class Agent(ABC):
    """Base class for agents."""

    name: str
    """Name of the agent. Must be unique.
    Other agents use this name to refer to it.
    It is also displayed in the list of agents."""

    description: str
    """Description of the agent.
    It tells what the agent can do. Used during planning."""

    def __repr__(self):
        return f"Agent<{self.name}>"

    Return = Generator[str | Image, None, None]

    @abstractmethod
    def message(self, input: str) -> Return:
        """Sends a message to the agent. Agents should remember previous messages."""

    def history(self) -> list[MessageDict]:
        """Optional. Agent implementation should return a list of previous messages."""
        return []
