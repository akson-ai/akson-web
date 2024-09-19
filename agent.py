import os
import datetime
from textwrap import dedent
from typing import Sequence

from pydantic import Field
from openai import AzureOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
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
        reply = agent.message(self.message, sender=self.context.agent, session_id=None)
        return f"The message is sent to the agent. The reply is:\n{reply}"


class CurrentTime(Function):
    """Returns the current time."""

    def run(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


Thread = list[ChatCompletionMessageParam]


class Threads:

    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self.store: dict[str, Thread] = {}

    def get(self, session_id: str | None) -> Thread:
        if not session_id:
            return self._create()
        try:
            return self.store[session_id]
        except KeyError:
            thread = self._create()
            self.store[session_id] = thread
            return thread

    def _create(self) -> Thread:
        return [ChatCompletionSystemMessageParam(role="system", content=self.system_prompt)]


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
        self.tools = tools

        self.toolset = Toolset(self, *tools)
        self.client = AzureOpenAI()
        self.threads = Threads(self.prompt)

    def message(self, input: str, *, sender: str, session_id: str | None) -> str | None:
        logger.warning("%s -> %s: %s", sender, self.name, input)

        thread = self.threads.get(session_id)

        completion = self._complete([ChatCompletionUserMessageParam(role="user", content=input)], thread)
        tool_calls = self.toolset.process_response(completion, self.name)
        while tool_calls:
            completion = self._complete(tool_calls, thread)
            tool_calls = self.toolset.process_response(completion, self.name)

        return completion.choices[0].message.content

    def _complete(self, messages: Sequence[ChatCompletionMessageParam], thread: Thread) -> ChatCompletion:
        thread.extend(messages)

        logger.info("Completing chat for %s", self.name)
        for message in thread:
            logger.debug(message)

        completion = self.client.chat.completions.create(
            model=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            messages=thread,
            **self._tool_kwargs(),
        )

        message = completion.choices[0].message
        thread.append(
            ChatCompletionAssistantMessageParam(
                role="assistant", content=message.content, tool_calls=message.tool_calls
            )
        )
        logger.debug(thread[-1])

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
