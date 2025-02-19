"""
Global registry for agents.
"""

from framework import Assistant

# Global dictionary of registered agents.
assistants: dict[str, Assistant] = {}


def register(name: str, assistant: Assistant):
    assistants[name] = assistant


def get(name: str) -> Assistant:
    return assistants[name]


def list() -> list[Assistant]:
    """Returns a list of all registered agents that can be used by Planner agent."""
    return [assistant for assistant in assistants.values()]
