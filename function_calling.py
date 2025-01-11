import json
from inspect import Parameter, getdoc, signature
from typing import Any, Callable, Union, get_args, get_origin, get_type_hints

import docstring_parser
from openai import NOT_GIVEN, pydantic_function_tool
from openai.lib._parsing._completions import parse_chat_completion
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
)
from pydantic import BaseModel, Field, create_model

from logger import logger


class Toolset:
    """Manages the list of tools to be passed into completion reqeust."""

    def __init__(self, owner, tools: list[Callable]) -> None:
        self.owner = owner
        self.functions = {f.__name__: f for f in tools}

    def openai_schema(self) -> list[ChatCompletionToolParam]:
        """Returns the list of tools to be passed into completion reqeust."""
        return [pydantic_function_tool(function_to_pydantic_model(f)) for f in self.functions.values()]

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
            assert isinstance(instance, BaseModel)
            func = self.functions[function.name]
            kwargs = {name: getattr(instance, name) for name in instance.model_fields}
            result = func(**kwargs)
            logger.info("%s call result: %s", function.name, result)
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})

        return messages


def get_type_string(python_type):
    """Convert Python type to JSON schema type string"""
    if python_type is str:
        return "string"
    elif python_type is int:
        return "integer"
    elif python_type is float:
        return "number"
    elif python_type is bool:
        return "boolean"
    elif python_type is list or get_origin(python_type) is list:
        return "array"
    elif python_type is dict or get_origin(python_type) is dict:
        return "object"
    elif isinstance(python_type, type) and issubclass(python_type, BaseModel):
        return "object"
    return "string"


def function_to_pydantic_model(func):
    sig = signature(func)
    type_hints = get_type_hints(func)
    docstring = getdoc(func)
    parsed_docstring = docstring_parser.parse(docstring) if docstring else None
    param_descriptions = {
        param.arg_name: param.description for param in (parsed_docstring.params if parsed_docstring else [])
    }

    fields = {}
    for param_name, param in sig.parameters.items():
        field_type = type_hints.get(param_name, Parameter.empty)
        default = param.default

        # Handle missing type hints
        if field_type is Parameter.empty:
            field_type = Any

        # Handle Optional types
        if get_origin(field_type) is Union:
            args = get_args(field_type)
            if type(None) in args:
                field_type = next(arg for arg in args if arg is not type(None))
                if default is Parameter.empty:
                    default = None

        if default is Parameter.empty:
            default = ...

        fields[param_name] = (
            field_type,
            Field(
                default=default,
                description=param_descriptions.get(param_name, None),
                json_schema_extra={"type": get_type_string(field_type)},
            ),
        )

    return create_model(
        func.__name__,
        __doc__=parsed_docstring.short_description if parsed_docstring else None,
        **fields,
    )
