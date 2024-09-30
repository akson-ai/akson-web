import importlib
import os

from agent import Agent
from logger import logger


def load_agents() -> dict[str, Agent]:
    agents = {}
    agents_dir = os.path.join(os.path.dirname(__file__), "agents")
    logger.info("Agents directory: %s", agents_dir)
    for agent_file in os.listdir(agents_dir):
        agent_file = os.path.basename(agent_file)
        module_name, extension = os.path.splitext(agent_file)
        if extension != ".py":
            continue
        module_name = f"agents.{module_name}"
        logger.info("Loading file: %s", agent_file)
        module = importlib.import_module(module_name)
        agent = module.agent
        if not isinstance(agent, Agent):
            continue
        agents[agent.name] = agent
        logger.info("Agent loaded: %s", agent.name)
    return agents
