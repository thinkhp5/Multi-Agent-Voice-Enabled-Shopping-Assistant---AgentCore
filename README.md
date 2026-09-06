RetailTherapy — AgentCore + MCP Edition
A rebuild of the original Multi-Agent-Voice-Enabled-Shopping-Assistant retargeted to deploy on Amazon Bedrock AgentCore Runtime, with tools exposed as an MCP server instead of local Python functions.

The LangGraph orchestration (orchestrator → parallel product/support agents → synthesizer, with HITL interrupts) is unchanged in shape. What changed:

Original	This version
Tools are local Python functions in tools.py	Tools live in a standalone MCP server (mcp_server/server.py), callable by any MCP client, any framework
MemorySaver (in-process, lost on restart)	Pluggable checkpointer — MemorySaver for local dev, AgentCore Memory adapter for production
Run via python -m src.main (local CLI)	Hosted on AgentCore Runtime behind runtime_app.py, invoked over HTTPS
Single deployable	Two deployables: the agent (Runtime, HTTP protocol) and the MCP tool server (Runtime, MCP protocol) — can scale/version independently
Architecture
                        ┌─────────────────────────────┐
   User / Voice   ───▶  │  AgentCore Runtime (agent)   │
                        │  runtime_app.py               │
                        │  → LangGraph: orchestrator     │
                        │    ├─ product_agent  ─┐        │
                        │    └─ support_agent  ─┼─▶ synth │
                        └──────────┬─────────────┘
                                   │ MCP (streamable-http)
                                   ▼
                        ┌─────────────────────────────┐
                        │  AgentCore Runtime (MCP)     │
                        │  mcp_server/server.py         │
                        │  tools:                       │
                        │   - search_product_catalog    │
                        │   - get_order_status           │
                        │   - escalate_to_human           │
                        └─────────────────────────────┘
Both halves deploy independently via the agentcore CLI. The agent side never imports tool implementations directly — it only knows the MCP server's URL, exactly like it would for a third-party MCP server.

Project layout
retailtherapy-agentcore/
├── src/
│   ├── config.py        # env/config, model client (Bedrock Claude via langchain_aws)
│   ├── state.py          # LangGraph state TypedDicts
│   ├── data.py            # static product catalog + order DB (swap for real APIs later)
│   ├── rag.py              # vector store for product catalog semantic search
│   ├── mcp_tool_client.py  # MCP client wiring used inside the agent's nodes
│   ├── nodes.py             # orchestrator / product_agent / support_agent / synthesizer
│   ├── graph.py              # builds the StateGraph, checkpointer selection
│   └── memory_checkpointer.py # AgentCore Memory-backed checkpointer adapter
├── mcp_server/
│   └── server.py          # FastMCP tool server (deploys to AgentCore Runtime, MCP protocol)
├── runtime_app.py          # AgentCore Runtime entrypoint (HTTP protocol) for the agent
├── requirements.txt
├── requirements-mcp.txt
├── .env.example
└── DEPLOY.md               # step-by-step agentcore CLI deployment
Local development
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-mcp.txt

cp .env.example .env   # fill in AWS creds / region / model id

# Terminal 1 — run the MCP tool server locally
python -m mcp_server.server

# Terminal 2 — run the agent locally against the local MCP server
python runtime_app.py --local
Deploying to AWS
See DEPLOY.md for the full agentcore configure / agentcore deploy sequence for both the MCP server and the agent, including how to wire the agent's MCP_SERVER_URL to the deployed MCP server's Runtime ARN.
