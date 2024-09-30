import os

from langchain_core.chat_history import (
    BaseChatMessageHistory,
    InMemoryChatMessageHistory,
)
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import AzureChatOpenAI

from agent import Agent


class Assistant(Agent):

    name = "Assistant"
    description = "An agent that helps a user."

    def __init__(self):
        model = AzureChatOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            api_version=os.environ["OPENAI_API_VERSION"],
            temperature=0,
        )
        self.chain = RunnableWithMessageHistory(model, self.get_session_history)
        self.store = {}

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in self.store:
            self.store[session_id] = InMemoryChatMessageHistory()
        return self.store[session_id]

    def message(self, input: str, *, session_id: str | None) -> str:
        config: RunnableConfig = {"configurable": {"session_id": session_id}}
        response = self.chain.invoke([HumanMessage(content=input)], config=config)
        return response.content


agent = Assistant()
