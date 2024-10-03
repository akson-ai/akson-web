import os

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel

from agent import Agent

model = AzureChatOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    api_version=os.environ["OPENAI_API_VERSION"],
    temperature=0,
)


@tool
def search_web(query: str):
    """Call to surf the web."""
    return "TODO"


@tool
def send_email(to: str, subject: str, body: str):
    """Send an email."""
    return "TODO"


@tool
def ask_llm(question: str):
    """Ask the LLM a question."""
    return "TODO"


tools = [search_web, send_email, ask_llm]


class Subtask(BaseModel):
    subtask: str
    tool: str


class Plan(BaseModel):
    subtasks: list[Subtask]


class AgentState(MessagesState):
    task: str
    plan: Plan


def extract_task(state: AgentState):
    class ExtractTask(BaseModel):
        task: str | None
        response: str

    system_prompt = """
        You are an AI assistant that helps the user with their task.
        Keep a conversation going with the user.
        If the user asks for a task, respond with the task.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("placeholder", "{messages}"),
        ]
    )
    llm = model.with_structured_output(ExtractTask)
    chain = prompt | llm
    response = chain.invoke({"messages": state["messages"]})
    assert isinstance(response, ExtractTask)
    print(f"Task: {response.task}, Response: {response.response}")
    if response.task:
        return {"task": response.task}
    else:
        return {"messages": [AIMessage(content=response.response)]}


def planner(state: AgentState):
    class DivideSubtasks(BaseModel):
        plan: Plan

    system_prompt = """
        You are a helpful assistant that divides the given task into subtasks.
        Match each subtask to the tool that will help complete it.

        You have access to the following tools:
        {tools}
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("placeholder", "{messages}"),
        ]
    )
    llm = model.with_structured_output(DivideSubtasks)
    chain = prompt | llm
    response = chain.invoke(
        {
            "messages": [HumanMessage(content=f"Task: {state['task']}")],
            "tools": tools,
        }
    )
    assert isinstance(response, DivideSubtasks)
    print(f"Plan: {response.plan}")
    return {
        "plan": response.plan,
    }


def executor(state: AgentState):
    messages = []
    for step in state["plan"].subtasks:
        messages.append(f"Executing: {step.subtask} with {step.tool}")

    return {
        "messages": "\n".join(messages),
        "plan": None,
    }


def route_task(state: AgentState) -> str:
    if state.get("task"):
        return "planner"
    else:
        return END


def create_graph():
    graph = StateGraph(AgentState)

    graph.add_node(extract_task)
    graph.add_node(planner)
    graph.add_node(executor)

    graph.add_edge(START, "extract_task")
    graph.add_conditional_edges("extract_task", route_task)
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


class Assistant(Agent):

    name = "Assistant"
    description = "An agent that helps users with their tasks."

    def __init__(self):
        self.graph = create_graph()

    def message(self, input: str, *, session_id: str | None) -> str:
        final_state = self.graph.invoke(
            {"messages": [HumanMessage(content=input)]},
            config={"configurable": {"thread_id": session_id}},
        )
        return final_state["messages"][-1].content


agent = Assistant()
