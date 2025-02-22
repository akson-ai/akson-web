import asyncio
import json
import os
from abc import ABC, abstractmethod
from typing import Any, Callable, Iterator, Literal, Sequence, TypedDict

from fastapi import Request
from openai import AsyncAzureOpenAI
from openai.lib.streaming.chat import (
    ChunkEvent,
    ContentDeltaEvent,
    FunctionToolCallArgumentsDeltaEvent,
    RefusalDeltaEvent,
)
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
    ChatCompletionMessageToolCallParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ParsedChatCompletionMessage,
)
from openai.types.chat.chat_completion_message_tool_call_param import Function

from function_calling import Toolset
from logger import logger

# class Agent(ABC):
#     """Base class for agents."""

#     name: str
#     """Name of the agent. Must be unique.
#     Other agents use this name to refer to it.
#     It is also displayed in the list of agents."""

#     description: str
#     """Description of the agent.
#     It tells what the agent can do. Used during planning."""

#     def __repr__(self):
#         return f"Agent<{self.name}>"

#     Reply = str | Iterator[str] | Image
#     Return = Iterator[Reply]

#     @abstractmethod
#     def message(self, input: str) -> Return:
#         """Sends a message to the agent. Agents should remember previous messages."""


class Message(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class Chat:
    """Chat stores messages between the user and the agent."""

    def __init__(self):
        self.messages: list[Message] = []  # TODO encapsulate messages
        self._request: Request | None
        self._queue = asyncio.Queue()

    async def add_message(self, message: str | Iterator[str]):
        await self._queue.put({"control": "new_message"})

        if isinstance(message, str):
            stream = [message]
        else:
            stream = message

        chunks = []
        for chunk in stream:
            chunks.append(chunk)
            await self._queue.put({"chunk": chunk})

            assert isinstance(self._request, Request)
            if await self._request.is_disconnected():
                logger.info("Client disconnected, stopping streaming")
                break

        self.messages.append({"role": "assistant", "content": "".join(chunks)})

    async def begin_message(self):
        self._current_message = []
        await self._queue.put({"control": "new_message"})

    async def add_chunk(self, chunk: str):
        self._current_message.append(chunk)
        await self._queue.put({"chunk": chunk})

    async def end_message(self) -> str:
        message = "".join(self._current_message)
        self.messages.append({"role": "assistant", "content": message})
        await self._queue.put({"control": "end_message"})
        return message

    async def _send_control(self, code: str):
        await self._queue.put({"control": code})


class PersistentChat(Chat):
    """Chat that can be saved and loaded from a file."""

    def __init__(self, id: str):
        super().__init__()
        # TODO save in a dir
        self.filename = f"chat_{id}_messages.jsonl"

    def save(self):
        with open(self.filename, "w") as f:
            for message in self.messages:
                json.dump(message, f)
                f.write("\n")

    def load(self):
        with open(self.filename, "r") as f:
            for line in f:
                message = json.loads(line)
                self.messages.append(message)


class Assistant(ABC):
    """Assistants are used to generate responses to chats."""

    # TODO set name and description
    # def __repr__(self):
    #     return f"Assistant<{self.name}>"

    @abstractmethod
    async def run(self, chat: Chat) -> None: ...


class SimpleAssistant(Assistant):
    """Simple assistant that uses OpenAI's chat API to generate responses."""

    def __init__(self, system_prompt: str, functions: list[Callable] = []):
        self.system_prompt = system_prompt
        self._client = AsyncAzureOpenAI()
        self._toolset = Toolset(self, functions)

    async def run(self, chat: Chat) -> None:
        logger.debug(f"Completing chat...\nLast message: {chat.messages[-1]}")

        # These messages are sent to OpenAI in chat completion request.
        # Here, we convert chat messages in web UI to OpenAI format.
        messages = self._get_openai_messages(chat)

        message = await self._complete(messages, chat)
        messages.append(_convert_assistant_message(message))

        # We keep continue hitting OpenAI API until there are no more tool calls.
        while message.tool_calls:
            tool_calls = self._toolset.process_tool_calls(message.tool_calls)
            messages.extend(tool_calls)

            message = await self._complete(messages, chat)
            messages.append(_convert_assistant_message(message))

    def _get_openai_messages(self, chat: Chat) -> list[ChatCompletionMessageParam]:
        messages: Sequence[ChatCompletionMessageParam] = []
        messages.append(ChatCompletionSystemMessageParam(role="system", content=self.system_prompt))
        for message in chat.messages:
            if message["role"] == "user":
                messages.append(ChatCompletionUserMessageParam(role="user", content=message["content"]))
            elif message["role"] == "assistant":
                messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=message["content"]))
        return messages

    async def _complete(self, messages: list[ChatCompletionMessageParam], chat: Chat) -> ParsedChatCompletionMessage:
        logger.info("Completing chat")
        for message in messages:
            logger.debug(message)

        await chat.begin_message()

        async with self._client.beta.chat.completions.stream(
            model=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            messages=messages,
            **self._tool_kwargs(),
        ) as stream:
            async for event in stream:
                match event:  # https://github.com/openai/openai-python/blob/main/helpers.md#chat-completions-events
                    case ContentDeltaEvent():
                        await chat.add_chunk(event.delta)
                    case RefusalDeltaEvent():
                        await chat.add_chunk(event.delta)
                    case FunctionToolCallArgumentsDeltaEvent():
                        await chat.add_chunk(event.arguments_delta)
                    case ChunkEvent() if event.chunk.choices[0].finish_reason:
                        await chat.end_message()
                        choice = event.snapshot.choices[0]
                        if choice.finish_reason in ("stop", "tool_calls"):
                            return choice.message
                        raise NotImplementedError(f"finish_reason={choice.finish_reason}")

        raise Exception("Stream ended unexpectedly")

    def _tool_kwargs(self) -> dict[str, Any]:
        tools = self._toolset.openai_schema()
        if tools:
            return {"tools": tools, "tool_choice": "auto", "parallel_tool_calls": False}
        return {}


def _convert_assistant_message(message: ParsedChatCompletionMessage) -> ChatCompletionAssistantMessageParam:
    if message.tool_calls:
        tool_calls = list(map(_convert_tool_call, message.tool_calls))
        return ChatCompletionAssistantMessageParam(role="assistant", content=message.content, tool_calls=tool_calls)
    else:
        return ChatCompletionAssistantMessageParam(role="assistant", content=message.content)


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


# class StructuredOutput:
#     """Get structured output from a chat model."""

#     def __init__(self, system_prompt: str, response_format: type[BaseModel]):
#         self.system_prompt = system_prompt
#         self.response_format = response_format
#         self._chat = Chat()
#         self._client = AzureOpenAI()

#     def add_example(self, user_message: str, response: BaseModel):
#         """Add an example to the prompt."""
#         self._chat.messages.extend(
#             [
#                 {"role": "system", "name": "example_user", "content": user_message},
#                 {"role": "system", "name": "example_assistant", "content": response.model_dump_json()},
#             ]
#         )

#     def run(self, chat: Chat) -> object:
#         """Run the system prompt on chat and return the parsed response."""
#         response = self._client.beta.chat.completions.parse(
#             model=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
#             response_format=self.response_format,
#             messages=self._chat.messages + chat.messages,
#         )
#         instance = response.choices[0].message.parsed
#         assert isinstance(instance, self.response_format)
#         return instance

#     def run_user_message(self, user_message: str) -> object:
#         """Run the system prompt on a user message and return the parsed response."""
#         chat = Chat()
#         chat.messages.append({"role": "user", "content": user_message})
#         return self.run(chat)


# class ChatAgent(Agent):

#     def __init__(self, name: str, description: str, assistant: Assistant):
#         super().__init__()
#         self.name = name
#         self.description = description
#         self.assistant = assistant
#         self.chat = PersistentChat(name)
#         try:
#             self.chat.load()
#         except FileNotFoundError:
#             pass

#     def message(self, input: str) -> Agent.Return:
#         if input.strip() == "/clear":
#             self.chat.clear()
#             response = "Chat cleared"
#         else:
#             self.chat.messages.append({"role": "user", "content": input})
#             response = self.assistant.run(self.chat)
#             self.chat.messages.append({"role": "assistant", "content": response})
#         self.chat.save()
#         yield response


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

    chat = Chat()
    chat.messages.append({"role": "user", "content": "What is three plus one?"})

    mathematician = Mathematician()
    message = mathematician.run(chat)

    print("Response:", message)
