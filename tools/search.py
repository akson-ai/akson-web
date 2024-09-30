import os

from exa_py.api import Exa
from pydantic import Field

from function_calling import Function


class Search(Function):
    """Search the web for relevant information."""

    query: str = Field(description="The query to search for.")

    def run(self):
        exa = Exa(os.environ["EXA_API_KEY"])

        response = exa.search_and_contents(
            self.query,
            num_results=5,
            use_autoprompt=True,
            text={"max_characters": 1000},
            highlights=True,
        )

        output = ""
        for result in response.results:
            output += f"Title: {result.title}"
            output += f"URL: {result.url}"
            output += f"Text snippet: {result.text[:200]}..."
            output += "---"

        return output
