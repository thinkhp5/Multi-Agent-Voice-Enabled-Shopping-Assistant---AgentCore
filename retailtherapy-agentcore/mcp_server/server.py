"""
RetailTherapy MCP tool server.

Exposes the three tools the original repo had as local Python functions
(`search_product_catalog`, `get_order_status`, `escalate_to_human`) as MCP
tools instead — callable by this LangGraph agent, or by any other MCP
client/framework (Strands, CrewAI, a completely different customer's stack).

Deploy target: Amazon Bedrock AgentCore Runtime, MCP protocol.
Per AWS's MCP protocol contract, AgentCore Runtime requires:
  - stateless streamable-HTTP transport
  - host 0.0.0.0, port 8000
  - served at /mcp

Run locally:
    python -m mcp_server.server

Deploy:
    agentcore configure -e mcp_server/server.py --protocol MCP
    agentcore deploy
"""
import uuid

from mcp.server.fastmcp import FastMCP

from src.data import ORDER_DB, SUPPORT_ESCALATION_POLICY
from src.rag import search_products

# stateless_http=True is required for AgentCore Runtime's session-isolation model —
# don't rely on in-memory state between calls; use session_id / order_id lookups instead.
mcp = FastMCP("retailtherapy-tools", stateless_http=True, host="0.0.0.0", port=8000)


@mcp.tool()
def search_product_catalog(query: str) -> list[dict]:
    """
    Semantic search over the product catalog.

    Args:
        query: Natural-language product description, e.g. "wireless headphones under $50".

    Returns:
        Up to 3 matching products with id, name, category, price, description.
    """
    return search_products(query, k=3)


@mcp.tool()
def get_order_status(order_id: str | None = None, customer_email: str | None = None) -> dict:
    """
    Look up an order by order ID or customer email.

    Args:
        order_id: Order identifier, e.g. "ORD102".
        customer_email: Customer's email, used if order_id isn't provided.

    Returns:
        Order details (status, ETA, notes), or an error message if not found.
    """
    if order_id and order_id in ORDER_DB:
        return ORDER_DB[order_id]

    if customer_email:
        for order in ORDER_DB.values():
            if order["customer_email"].lower() == customer_email.lower():
                return order

    return {"error": "No matching order found. Please double check the order ID or email."}


@mcp.tool()
def escalate_to_human(summary: str, priority: str = "MEDIUM") -> dict:
    """
    Create a human support escalation ticket.

    Args:
        summary: Short description of the customer's issue.
        priority: "HIGH", "MEDIUM", or "LOW".

    Returns:
        Ticket ID, priority, and the response-time commitment for that priority.

    NOTE: This tool has a real side effect (creates a ticket / notifies a human).
    In production, gate this behind AgentCore Identity so the call carries the
    calling user's identity rather than a shared service credential, and route
    the actual notification (e.g. Resend/email) through a securely-stored,
    per-tenant credential rather than an env var baked into this server.
    """
    priority = priority.upper() if priority.upper() in SUPPORT_ESCALATION_POLICY else "MEDIUM"
    ticket_id = f"ESC-{uuid.uuid4().hex[:6].upper()}"
    return {
        "ticket_id": ticket_id,
        "priority": priority,
        "summary": summary,
        "commitment": SUPPORT_ESCALATION_POLICY[priority],
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
