import os

import requests

from framework import Assistant, Chat

PERPLEXITY_API_KEY = os.environ["PERPLEXITY_API_KEY"]


class Perplexity(Assistant):

    async def run(self, chat: Chat) -> None:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "sonar",
            "messages": chat.state.messages,
        }
        response = requests.request("POST", url, json=payload, headers=headers)
        data = response.json()

        message = data["choices"][0]["message"]
        assert message["role"] == "assistant"
        await chat.add_message(message["content"])

        citations = "\n".join(f"[{i}] {citation}" for i, citation in enumerate(data["citations"], 1))
        await chat.add_message(citations)


perplexity = Perplexity()
