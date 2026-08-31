"""
AgentCore Runtime entrypoint for the RetailTherapy agent.

This is the HTTP-protocol Runtime app (as opposed to mcp_server/server.py,
which is a separate MCP-protocol Runtime app). It hosts the compiled
LangGraph (orchestrator -> product_agent/support_agent -> synthesizer) and
handles both normal turns and HITL interrupt/resume.

Local run:
    python runtime_app.py --local

Deploy:
    agentcore configure -e runtime_app.py
    agentcore deploy
"""
import argparse
import asyncio

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langgraph.types import Command

from src.graph import build_graph

app = BedrockAgentCoreApp()
_graph = build_graph()


@app.entrypoint
async def invoke(payload: dict):
    """
    Expected payload shape:
      {"prompt": "...", "session_id": "..."}                # normal turn
      {"resume": "ORD102", "session_id": "..."}              # resuming after HITL interrupt
    """
    session_id = payload.get("session_id", "default-session")
    config = {"configurable": {"thread_id": session_id}}

    if "resume" in payload:
        result = await _graph.ainvoke(Command(resume=payload["resume"]), config=config)
    else:
        result = await _graph.ainvoke(
            {"user_query": payload["prompt"], "session_id": session_id},
            config=config,
        )

    if "__interrupt__" in result:
        # Graph paused for missing info (e.g. order ID) — surface the question
        # to the caller; they should respond with {"resume": "...", "session_id": ...}
        return {
            "status": "interrupted",
            "question": result["__interrupt__"][0].value,
            "session_id": session_id,
        }

    return {"status": "complete", "answer": result["final_answer"], "session_id": session_id}


def _local_repl():
    """Quick local text REPL, mirroring the original repo's CLI mode."""
    print("RetailTherapy (local, AgentCore-shaped) — type 'quit' to exit\n")
    session_id = "local-session"
    pending_interrupt = False

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "quit":
            break

        payload = (
            {"resume": user_input, "session_id": session_id}
            if pending_interrupt
            else {"prompt": user_input, "session_id": session_id}
        )
        result = asyncio.run(invoke(payload))

        if result["status"] == "interrupted":
            print(f"🔄 Assistant asks: {result['question']}")
            pending_interrupt = True
        else:
            print(f"Assistant: {result['answer']}\n")
            pending_interrupt = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true", help="Run a local text REPL instead of the Runtime server.")
    args = parser.parse_args()

    if args.local:
        _local_repl()
    else:
        app.run()
