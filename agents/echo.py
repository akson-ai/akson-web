from agent import Agent


class Echo(Agent):
    name = "Echo"
    description = "An agent that echoes the user's message."
    prompt = """
        You are a helpful assistant that echoes the user's message.
    """


agent = Echo()
