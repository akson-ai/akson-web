import os
import datetime
from textwrap import dedent

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


class Agent:

    def __init__(self, name: str, description: str, prompt: str, tools: list[type[Function]] = []):
        """
        Args:
            name: Name of the agent. Must be unique. Other agents use this name to refer to it.
            description: Description of the agent. It tells what the agent can do. Used during planning.
            prompt: Prompt for the agent. They are instructions for the agent.
            tools: List of tools the agent can use.
        """
        self.name = name
        self.description = dedent(description).strip()
        self.prompt = dedent(prompt).strip()
        self.toolset = Toolset(self, *tools)
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

    def _tool_kwargs(self) -> dict:
        tools = self.toolset.openai_schema()
        if not tools:
            return {}
        return {
            "tools": tools,
            "tool_choice": "auto",
            "parallel_tool_calls": False,
        }
