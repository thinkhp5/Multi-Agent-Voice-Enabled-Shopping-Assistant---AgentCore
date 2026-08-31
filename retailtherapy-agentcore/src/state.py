"""LangGraph state definitions — same shape as the original repo's state.py."""
import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentTask(TypedDict):
    agent: str  # "product_agent" | "support_agent"
    instructions: str


def agent_results_reducer(
    existing: list[dict], new: list[dict]
) -> list[dict]:
    """Empty list resets (clears stale results from prior turns); otherwise append."""
    if not new:
        return []
    return existing + new


class RetailTherapyState(TypedDict):
    messages: Annotated[list, add_messages]
    user_query: str
    session_id: str
    tasks: list[AgentTask]
    requires_synthesis: bool
    agent_results: Annotated[list[dict], agent_results_reducer]
    final_answer: str


class WorkerInput(TypedDict):
    """Input passed into each parallel subgraph via Send()."""
    messages: Annotated[list, add_messages]
    instructions: str
    session_id: str
