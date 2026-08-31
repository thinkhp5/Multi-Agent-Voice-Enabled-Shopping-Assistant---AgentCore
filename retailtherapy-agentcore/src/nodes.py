"""
Graph nodes — same four-node shape as the original repo (orchestrator,
product_agent, support_agent, synthesizer), but product_agent and
support_agent now call tools over MCP instead of local functions.
"""
import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.types import Command, Send, interrupt

from src.config import get_chat_model, logger
from src.mcp_tool_client import get_mcp_tools
from src.state import RetailTherapyState, WorkerInput

PRODUCT_PROMPT = (
    "You are the product discovery specialist for RetailTherapy. Use the "
    "search_product_catalog tool to find relevant items and answer helpfully. "
    "Keep responses concise and specific (names, prices, one-line why-it-fits)."
)

SUPPORT_PROMPT = (
    "You are the support specialist for RetailTherapy. Use get_order_status to "
    "look up orders (you need an order ID or the customer's email — ask if "
    "missing) and escalate_to_human for anything you can't resolve. Be "
    "empathetic and concrete about ETAs and next steps."
)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
async def orchestrator_node(state: RetailTherapyState):
    model = get_chat_model()
    classification_prompt = SystemMessage(
        content=(
            "Classify the customer's message. Decide whether it needs the "
            "product_agent, the support_agent, or both. Respond ONLY with JSON: "
            '{"tasks": [{"agent": "product_agent"|"support_agent", '
            '"instructions": "..."}]}'
        )
    )
    response = await model.ainvoke([classification_prompt, HumanMessage(content=state["user_query"])])

    try:
        parsed = json.loads(response.content)
        tasks = parsed["tasks"]
    except (json.JSONDecodeError, KeyError):
        logger.warning("Orchestrator classification failed to parse, defaulting to product_agent.")
        tasks = [{"agent": "product_agent", "instructions": state["user_query"]}]

    requires_synthesis = len(tasks) > 1

    sends = [
        Send(
            task["agent"],
            WorkerInput(
                messages=[HumanMessage(content=task["instructions"])],
                instructions=task["instructions"],
                session_id=state["session_id"],
            ),
        )
        for task in tasks
    ]
    return Command(
        update={"tasks": tasks, "requires_synthesis": requires_synthesis, "agent_results": []},
        goto=sends,
    )


# ---------------------------------------------------------------------------
# Product agent (model <-> MCP tools loop)
# ---------------------------------------------------------------------------
async def product_agent(state: WorkerInput):
    tools = await get_mcp_tools()
    product_tools = [t for t in tools if t.name == "search_product_catalog"]
    model = get_chat_model().bind_tools(product_tools)

    messages = [SystemMessage(content=PRODUCT_PROMPT)] + state["messages"]
    response = await model.ainvoke(messages)

    while response.tool_calls:
        tool_messages = []
        for call in response.tool_calls:
            tool = next(t for t in product_tools if t.name == call["name"])
            result = await tool.ainvoke(call["args"])
            tool_messages.append(
                ToolMessage(content=str(result), tool_call_id=call["id"])
            )
        messages = messages + [response] + tool_messages
        response = await model.ainvoke(messages)

    return {"agent_results": [{"agent": "product_agent", "content": response.content}]}


# ---------------------------------------------------------------------------
# Support agent (model <-> MCP tools loop, with HITL interrupt for order ID)
# ---------------------------------------------------------------------------
async def support_agent(state: WorkerInput):
    tools = await get_mcp_tools()
    support_tools = [t for t in tools if t.name in ("get_order_status", "escalate_to_human")]
    model = get_chat_model().bind_tools(support_tools)

    messages = [SystemMessage(content=SUPPORT_PROMPT)] + state["messages"]
    response = await model.ainvoke(messages)

    has_prior_tool_call = any(isinstance(m, ToolMessage) for m in state["messages"])
    if not response.tool_calls and not has_prior_tool_call:
        # Model didn't call a tool and hasn't yet — almost certainly means it
        # needs missing info (order ID / email) from the customer. Pause the
        # whole graph and ask, same HITL pattern as the original repo.
        user_answer = interrupt(response.content)
        messages = messages + [AIMessage(content=response.content), HumanMessage(content=user_answer)]
        response = await model.ainvoke(messages)

    while response.tool_calls:
        tool_messages = []
        for call in response.tool_calls:
            tool = next(t for t in support_tools if t.name == call["name"])
            result = await tool.ainvoke(call["args"])
            tool_messages.append(
                ToolMessage(content=str(result), tool_call_id=call["id"])
            )
        messages = messages + [response] + tool_messages
        response = await model.ainvoke(messages)

    return {"agent_results": [{"agent": "support_agent", "content": response.content}]}


# ---------------------------------------------------------------------------
# Synthesizer
# ---------------------------------------------------------------------------
async def synthesizer_node(state: RetailTherapyState):
    results = state["agent_results"]

    if len(results) == 1:
        final_answer = results[0]["content"]
    else:
        model = get_chat_model()
        merged_context = "\n\n".join(f"[{r['agent']}]: {r['content']}" for r in results)
        response = await model.ainvoke(
            [
                SystemMessage(
                    content="Merge these specialist responses into one natural, coherent reply."
                ),
                HumanMessage(content=merged_context),
            ]
        )
        final_answer = response.content

    return {"final_answer": final_answer, "messages": [AIMessage(content=final_answer)]}
