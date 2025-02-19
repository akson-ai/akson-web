from framework import ChatAgent, SimpleAssistant

chatgpt = ChatAgent(
    name="ChatGPT",
    description="A chat agent that helps users to chat with ChatGPT.",
    assistant=SimpleAssistant("You are ChatGPT"),
)
