from framework import ConversationalAgent, SimpleAssistant

chatgpt = ConversationalAgent(
    name="ChatGPT",
    description="A chat agent that helps users to chat with ChatGPT.",
    assistant=SimpleAssistant("You are ChatGPT"),
)
