"""
Global registry for agents.
"""

from agent import Agent

# Global dictionary of registered agents.
agents: dict[str, Agent] = {}


def register(agent: Agent):
    agents[agent.name] = agent


def get(name: str) -> Agent:
    return agents[name]


def list() -> list[Agent]:
    """Returns a list of all registered agents that can be used by Planner agent."""
    return [agent for agent in agents.values() if not agent.system]
