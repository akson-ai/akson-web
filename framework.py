import json
import os
from typing import Any, Callable, Sequence

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

from agent import Agent
from function_calling import Toolset
from logger import logger


class Conversation:
    def __init__(self, name: str):
        self.messages: list[ChatCompletionMessageParam] = []
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


class Assistant:

    def __init__(self, prompt: str, functions: list[Callable] = []):
        self.prompt = prompt
        self._client = AzureOpenAI()
        self._toolset = Toolset(self, functions)

    def run(self, conversation: Conversation) -> str:
        print(f"Completing chat...\nLast message: {conversation.messages[-1]}")
        messages: Sequence[ChatCompletionMessageParam] = []
        messages.append(ChatCompletionSystemMessageParam(role="system", content=self.prompt))
        messages.extend(conversation.messages)

        completion = self._complete(messages)
        tool_calls = self._toolset.process_response(completion, agent="TODO")
        while tool_calls:
            messages.extend(tool_calls)
            completion = self._complete(messages)
            tool_calls = self._toolset.process_response(completion, agent="TODO")

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


class SimpleAssistant(Assistant):
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
        prompt = self.__class__.__doc__ or ""
        functions = [getattr(self, name) for name, func in self.__class__.__dict__.items() if callable(func)]
        super().__init__(prompt, functions)


class ConversationalAgent(Agent):

    def __init__(self, name: str, description: str, assistant: Assistant):
        super().__init__()
        self.name = name
        self.description = description
        self.assistant = assistant
        self.conversation = Conversation(name)
        try:
            self.conversation.load()
        except FileNotFoundError:
            pass

    def message(self, input: str, *, session_id: str | None):
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

    class Mathematician(SimpleAssistant):
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

    conversation = Conversation("test")
    conversation.messages.append({"role": "user", "content": "What is three plus one?"})

    mathematician = Mathematician()
    message = mathematician.run(conversation)

    print("Response:", message)
