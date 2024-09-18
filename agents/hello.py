from agent import Agent


class Hello(Agent):
    name = "Hello"
    description = "An agent that greets the user."
    prompt = """
        You are a helpful assistant that greet the user.
        Get the user's name and greet them.
    """


agent = Hello()
