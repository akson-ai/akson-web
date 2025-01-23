import json
import os
from abc import ABC, abstractmethod
from typing import Any, Callable, Generator, Sequence

from gradio.components import Image
from gradio.components.chatbot import MessageDict
from openai import AzureOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
    ChatCompletionMessageToolCallParam,
    ChatCompletionSystemMessageParam,
)
from openai.types.chat.chat_completion_message_tool_call_param import Function
from pydantic import BaseModel

from function_calling import Toolset
from logger import logger


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


class Conversation:
    """Converation is used to store messages between the user and the agent."""

    def __init__(self):
        self.messages: list[ChatCompletionMessageParam] = []


class PersistentConversation(Conversation):
    """Conversation that can be saved and loaded from a file."""

    def __init__(self, name: str):
        super().__init__()
        self.filename = f"{name.lower()}_messages.jsonl"

    def save(self):
        with open(self.filename, "w") as f:
            for message in self.messages:
                if message["role"] in ["user", "assistant"]:
                    json.dump(message, f)
                    f.write("\n")

    def load(self):
        with open(self.filename, "r") as f:
            for line in f:
                message = json.loads(line)
                self.messages.append(message)


class Assistant(ABC):
    """Assistants are used to generate responses to conversations."""

    @abstractmethod
    def run(self, conversation: Conversation) -> str: ...


class SimpleAssistant(Assistant):
    """Simple assistant that uses OpenAI's chat API to generate responses."""

    def __init__(self, system_prompt: str, functions: list[Callable] = []):
        self.system_prompt = system_prompt
        self._client = AzureOpenAI()
        self._toolset = Toolset(self, functions)

    def run(self, conversation: Conversation) -> str:
        logger.debug(f"Completing chat...\nLast message: {conversation.messages[-1]}")
        messages: Sequence[ChatCompletionMessageParam] = []
        messages.append(ChatCompletionSystemMessageParam(role="system", content=self.system_prompt))
        messages.extend(conversation.messages)

        completion = self._complete(messages)
        tool_calls = self._toolset.process_response(completion)
        while tool_calls:
            messages.extend(tool_calls)
            completion = self._complete(messages)
            tool_calls = self._toolset.process_response(completion)

        content = completion.choices[0].message.content
        assert isinstance(content, str)
        return content

    def _complete(self, messages: list[ChatCompletionMessageParam]) -> ChatCompletion:
        logger.info("Completing chat")
        for message in messages:
            logger.debug(message)

        completion = self._client.chat.completions.create(
            model=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            messages=messages,
            **self._tool_kwargs(),
        )

        message = completion.choices[0].message
        logger.info("%s: %s", message.role, message.content)
        messages.append(_convert_assistant_message(message))

        return completion

    def _tool_kwargs(self) -> dict[str, Any]:
        tools = self._toolset.openai_schema()
        if tools:
            return {"tools": tools, "tool_choice": "auto", "parallel_tool_calls": False}
        return {}


def _convert_assistant_message(message: ChatCompletionMessage) -> ChatCompletionAssistantMessageParam:
    if message.tool_calls:
        tool_calls = list(map(_convert_tool_call, message.tool_calls))
        return ChatCompletionAssistantMessageParam(role=message.role, content=message.content, tool_calls=tool_calls)
    else:
        return ChatCompletionAssistantMessageParam(role=message.role, content=message.content)


def _convert_tool_call(tool_call: ChatCompletionMessageToolCall) -> ChatCompletionMessageToolCallParam:
    return ChatCompletionMessageToolCallParam(
        id=tool_call.id,
        function=Function(
            name=tool_call.function.name,
            arguments=tool_call.function.arguments,
        ),
        type=tool_call.type,
    )


class DeclarativeAssistant(SimpleAssistant):
    """
    Declarative way to create an assistant.
    Class docstring is used as the prompt; methods are used as functions.

    Example:

        class Mathematician(SimpleAssistant):
            "You are a mathematician. You can answer questions about math."

            def add_two_numbers(self, a: int, b: int) -> int:
                return a + b
    """

    def __init__(self):
        prompt = self.__doc__ or ""
        functions = [getattr(self, name) for name, func in self.__class__.__dict__.items() if callable(func)]
        super().__init__(prompt, functions)


class StructuredOutput:
    """Get structured output from a chat model."""

    def __init__(self, system_prompt: str, response_format: type[BaseModel]):
        self.system_prompt = system_prompt
        self.response_format = response_format
        self._conversation = Conversation()
        self._client = AzureOpenAI()

    def add_example(self, user_message: str, response: BaseModel):
        """Add an example to the prompt."""
        self._conversation.messages.extend(
            [
                {"role": "system", "name": "example_user", "content": user_message},
                {"role": "system", "name": "example_assistant", "content": response.model_dump_json()},
            ]
        )

    def run(self, conversation: Conversation) -> object:
        """Run the system prompt on conversation and return the parsed response."""
        response = self._client.beta.chat.completions.parse(
            model=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            response_format=self.response_format,
            messages=self._conversation.messages + conversation.messages,
        )
        instance = response.choices[0].message.parsed
        assert isinstance(instance, self.response_format)
        return instance

    def run_user_message(self, user_message: str) -> object:
        """Run the system prompt on a user message and return the parsed response."""
        conversation = Conversation()
        conversation.messages.append({"role": "user", "content": user_message})
        return self.run(conversation)


class ConversationalAgent(Agent):

    def __init__(self, name: str, description: str, assistant: Assistant):
        super().__init__()
        self.name = name
        self.description = description
        self.assistant = assistant
        self.conversation = PersistentConversation(name)
        try:
            self.conversation.load()
        except FileNotFoundError:
            pass

    def message(self, input: str) -> Agent.Return:
        self.conversation.messages.append({"role": "user", "content": input})
        response = self.assistant.run(self.conversation)
        self.conversation.messages.append({"role": "assistant", "content": response})
        self.conversation.save()
        yield response

    def history(self) -> list[MessageDict]:
        ret = []
        for message in self.conversation.messages:
            if message["role"] in ["user", "assistant"]:
                ret.append({"role": message["role"], "content": message["content"]})  # type: ignore
        return ret


if __name__ == "__main__":

    class Mathematician(DeclarativeAssistant):
        """
        You are a mathematician. You are good at math. You can answer questions about math.
        """

        def add_two_numbers(self, a: int, b: int) -> int:
            """
            Add two numbers

            Args:
              a (int): The first number
              b (int): The second number

            Returns:
              int: The sum of the two numbers
            """
            return a + b

    conversation = Conversation()
    conversation.messages.append({"role": "user", "content": "What is three plus one?"})

    mathematician = Mathematician()
    message = mathematician.run(conversation)

    print("Response:", message)
