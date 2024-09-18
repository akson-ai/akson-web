import os
import datetime
from abc import ABC
from textwrap import dedent
from typing import Any

from pydantic import Field
from openai import AzureOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from function_calling import Toolset, Function
from logger import logger


class MessageAgent(Function):
    """Sends a message to an agent."""

    agent: str = Field(description="The name of the agent to send the message to.")
    message: str = Field(description="The message to send to the agent.")

    def run(self):
        import registry

        agent = registry.get(self.agent)
        reply = agent.message(self.context.agent, self.message)
        return f"The message is sent to the agent. The reply is:\n{reply}"


class CurrentTime(Function):
    """Returns the current time."""

    def run(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Agent(ABC):

    name: str
    """Name of the agent. Must be unique. Other agents use this name to refer to it."""

    description: str
    """Description of the agent. It tells what the agent can do. Used during planning."""

    system: bool = False
    """System agents are not intended to be used by end users.
    Registry does not return system agents in the list of agents."""

    prompt: str
    """Prompt for the agent. They are instructions for the agent. """

    tools: list[type[Function]] = []
    """List of tools the agent can use."""

    def __init__(self):
        super().__init__()

        self.toolset = Toolset(self, *self.tools)
        self.description = dedent(self.description).strip()
        self.prompt = dedent(self.prompt).strip()
        self.client = AzureOpenAI()
        self.messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=self.prompt)
        ]
        import registry; registry.register(self)  # fmt: skip  # noqa  # prevents circular import

    def message(self, sender: str, input: str) -> str | None:
        logger.warning("%s -> %s: %s", sender, self.name, input)

        completion = self._complete(ChatCompletionUserMessageParam(role="user", content=input))
        tool_calls = self.toolset.process_response(completion, self.name)
        while tool_calls:
            completion = self._complete(*tool_calls)
            tool_calls = self.toolset.process_response(completion, self.name)

        message = completion.choices[0].message
        self.messages.append({"role": message.role, "content": message.content})

        return message.content

    def _complete(self, *messages: ChatCompletionMessageParam) -> ChatCompletion:
        self.messages.extend(messages)

        logger.info("Completing chat for %s", self.name)
        for message in self.messages:
            logger.debug(message)

        completion = self.client.chat.completions.create(
            model=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            messages=self.messages,
            **self._tool_kwargs(),
        )

        message = completion.choices[0].message
        logger.info("%s: %s", self.name, message.content)
        self.messages.append(message)

        return completion

    def _tool_kwargs(self) -> dict[str, Any]:
        tools = self.toolset.openai_schema()
        if not tools:
            return {}
        return {
            "tools": tools,
            "tool_choice": "auto",
            "parallel_tool_calls": False,
        }
