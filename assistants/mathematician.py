from framework import DeclarativeAssistant


class Mathematician(DeclarativeAssistant):
    """
    You are a mathematician. You are good at math. You can answer questions about math.

    Use add_two_numbers function to add two numbers.
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


mathematician = Mathematician()
