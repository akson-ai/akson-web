from framework import FunctionToolset, SimpleAssistant

system_prompt = """
    You are a mathematician but you can only add two numbers.
    Refuse operations other than addition.
    Use add_two_numbers function to add two numbers.
"""


def add_two_numbers(a: int, b: int) -> int:
    """
    Add two numbers

    Args:
      a (int): The first number
      b (int): The second number

    Returns:
      int: The sum of the two numbers
    """
    return a + b


toolset = FunctionToolset([add_two_numbers])

mathematician2 = SimpleAssistant(name="Mathematician2", system_prompt=system_prompt, toolset=toolset)
