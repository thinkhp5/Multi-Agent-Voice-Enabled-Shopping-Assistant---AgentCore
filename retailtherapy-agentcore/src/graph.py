"""Builds and compiles the StateGraph — same topology as the original repo."""
from langgraph.graph import END, START, StateGraph

from src.memory_checkpointer import get_checkpointer
from src.nodes import orchestrator_node, product_agent, support_agent, synthesizer_node
from src.state import RetailTherapyState


def build_graph():
    builder = StateGraph(RetailTherapyState)

    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("product_agent", product_agent)
    builder.add_node("support_agent", support_agent)
    builder.add_node("synthesizer", synthesizer_node)

    builder.add_edge(START, "orchestrator")
    # orchestrator_node uses Command(goto=[Send(...), ...]) for parallel dispatch,
    # so no static edges are declared from orchestrator here.
    builder.add_edge("product_agent", "synthesizer")
    builder.add_edge("support_agent", "synthesizer")
    builder.add_edge("synthesizer", END)

    return builder.compile(checkpointer=get_checkpointer())
