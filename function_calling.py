import json
from inspect import Parameter, getdoc, signature
from typing import Callable, get_type_hints

import docstring_parser
from openai import pydantic_function_tool
from openai.types.chat import (
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ParsedFunctionToolCall,
)
from pydantic import BaseModel, Field, create_model

from logger import logger


class Toolset:
    """Manages the list of tools to be passed into completion reqeust."""

    def __init__(self, owner, functions: list[Callable]) -> None:
        self.owner = owner
        self.functions = {f.__name__: f for f in functions}

    def openai_schema(self) -> list[ChatCompletionToolParam]:
        """Returns the list of tools to be passed into completion reqeust."""
        return [pydantic_function_tool(function_to_pydantic_model(f)) for f in self.functions.values()]

    def process_tool_calls(self, tool_calls: list[ParsedFunctionToolCall]) -> list[ChatCompletionToolMessageParam]:
        """This is called each time a response is received from completion method."""
        logger.info("Number of tool calls: %s", len(tool_calls))
        messages = []
        for tool_call in tool_calls:
            function = tool_call.function
            logger.info("Tool call: %s(%s)", function.name, function.parsed_arguments)
            instance = function.parsed_arguments
            assert isinstance(instance, BaseModel)
            func = self.functions[function.name]
            kwargs = {name: getattr(instance, name) for name in instance.model_fields}

            # Fill in default values
            for param in signature(func).parameters.values():
                if param.default is not Parameter.empty:
                    kwargs[param.name] = param.default

            result = func(**kwargs)
            logger.info("%s call result: %s", function.name, result)
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})

        return messages


def function_to_pydantic_model(func):
    sig = signature(func)
    type_hints = get_type_hints(func)
    docstring = getdoc(func)
    func_description = None
    param_descriptions = {}
    if docstring:
        parsed_docstring = docstring_parser.parse(docstring)
        func_description = parsed_docstring.short_description
        if parsed_docstring:
            for param in parsed_docstring.params:
                param_descriptions[param.arg_name] = param.description

    fields = {}
    for param_name, param in sig.parameters.items():
        type_hint = type_hints.get(param_name, str)

        # All fields are required. Optional parameters are emulated by using a union type with null.
        if param.default is not Parameter.empty:
            type_hint |= None

        fields[param_name] = (type_hint, Field(description=param_descriptions.get(param_name, None)))

    return create_model(func.__name__, __doc__=func_description, **fields)
