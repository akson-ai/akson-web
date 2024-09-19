import json
from typing import Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

from pydantic import BaseModel
from openai import pydantic_function_tool, NOT_GIVEN
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionToolParam,
    ChatCompletionToolMessageParam,
)
from openai.lib._parsing._completions import parse_chat_completion

from logger import logger


@dataclass
class FunctionContext:
    """Context for a function call."""

    agent: str
    """Name of the agent that is calling the function."""


class Function(ABC, BaseModel):
    """Base class for functions that can be called from agents."""

    _context: FunctionContext

    @property
    def context(self) -> FunctionContext:
        return self._context

    @abstractmethod
    def run(self) -> Any: ...


class Toolset:
    """Manages the list of tools to be passed into completion reqeust."""

    def __init__(self, owner, *tools: type[Function]) -> None:
        self.owner = owner
        self.tools = tools

    def openai_schema(self) -> list[ChatCompletionToolParam]:
        """Returns the list of tools to be passed into completion reqeust."""
        return [pydantic_function_tool(tool) for tool in self.tools]

    def process_response(self, completion: ChatCompletion, *, agent: str) -> list[ChatCompletionToolMessageParam]:
        """This is called each time a response is received from completion method."""
        completion = parse_chat_completion(
            chat_completion=completion, input_tools=self.openai_schema(), response_format=NOT_GIVEN
        )

        tool_calls = completion.choices[0].message.tool_calls
        if not tool_calls:
            logger.debug("No tool calls")
            return []

        logger.info("Number of tool calls: %s", len(tool_calls))
        messages = []
        for tool_call in tool_calls:
            function = tool_call.function
            logger.info("%s calls tool: %s(%s)", agent, function.name, function.parsed_arguments)
            instance = function.parsed_arguments
            assert isinstance(instance, Function)
            instance._context = FunctionContext(agent=agent)
            result = instance.run()
            logger.info("%s call result: %s", function.name, result)
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})

        return messages
