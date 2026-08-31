"""
MCP client used inside the agent's product/support subgraphs.

The agent no longer imports tool functions directly (as the original
tools.py did) — it discovers and calls tools over MCP, exactly as it would
for any third-party MCP server. This is what makes the tool layer reusable
across frameworks (Strands, CrewAI, etc.), not just this LangGraph app.
"""
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.config import MCP_BEARER_TOKEN, MCP_SERVER_URL

_tools_cache = None


def _connection_config() -> dict:
    headers = {}
    if MCP_BEARER_TOKEN:
        headers["Authorization"] = f"Bearer {MCP_BEARER_TOKEN}"

    return {
        "retailtherapy": {
            "url": MCP_SERVER_URL,
            "transport": "streamable_http",
            "headers": headers,
        }
    }


async def get_mcp_tools():
    """
    Fetch (and cache) the LangChain-compatible tool list from the MCP server.

    Called once at cold start inside runtime_app.py / graph.py, then bound
    onto the product_agent and support_agent subgraphs via .bind_tools().
    """
    global _tools_cache
    if _tools_cache is not None:
        return _tools_cache

    client = MultiServerMCPClient(_connection_config())
    _tools_cache = await client.get_tools()
    return _tools_cache
