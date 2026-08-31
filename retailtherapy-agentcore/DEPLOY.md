# Deploying RetailTherapy to AgentCore

Two separate Runtime deployments: the MCP tool server first, then the agent
(which needs the tool server's URL).

## 0. Prerequisites

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-mcp.txt
aws sts get-caller-identity   # confirm you're on the right AWS account
```

## 1. Deploy the MCP tool server

```bash
agentcore configure -e mcp_server/server.py --protocol MCP
# Accept defaults; when prompted for execution role, let it auto-create one
# with permissions for Runtime + Bedrock (needed for the embeddings call
# inside search_product_catalog).

agentcore deploy
```

Note the deployed Runtime ARN from the output — you'll need it in step 3.

Sanity check it's up:
```bash
agentcore invoke --protocol MCP '{"method": "tools/list"}'
```
You should see `search_product_catalog`, `get_order_status`, and
`escalate_to_human` in the response.

## 2. Get an invocation URL + bearer token for the MCP server

```bash
agentcore status   # shows the Runtime ARN + any Cognito/OAuth setup needed
```

Construct the MCP endpoint:
```
https://bedrock-agentcore.<region>.amazonaws.com/runtimes/<url-encoded-arn>/invocations?qualifier=DEFAULT
```

If you configured Cognito auth during `agentcore configure`, grab a bearer
token per the CLI's printed instructions (or `util/cognito-setup.sh`-style
script if you added one).

## 3. Point the agent at the deployed MCP server

Update `.env` (or set these as Runtime environment variables in step 4):
```
MCP_SERVER_URL=https://bedrock-agentcore.<region>.amazonaws.com/runtimes/<url-encoded-arn>/invocations?qualifier=DEFAULT
MCP_BEARER_TOKEN=<token from step 2>
```

## 4. Deploy the agent

```bash
agentcore configure -e runtime_app.py
# Accept defaults; auto-create execution role again (needs Bedrock + the
# ability to call the MCP server's Runtime endpoint).

agentcore deploy
```

## 5. Invoke it

```bash
agentcore invoke '{"prompt": "Do you have wireless headphones under $300?", "session_id": "demo-1"}'
```

Test the HITL flow:
```bash
agentcore invoke '{"prompt": "Where is my order?", "session_id": "demo-2"}'
# -> {"status": "interrupted", "question": "Could you provide your order ID or email?", ...}

agentcore invoke '{"resume": "ORD102", "session_id": "demo-2"}'
# -> {"status": "complete", "answer": "Your order ORD102 ... delayed ..."}
```

## 6. (Optional) Register the MCP server as a Gateway target instead

If you want other teams/agents (not just this LangGraph app) to discover
these tools through a shared catalog rather than a hardcoded URL, register
the same Runtime-hosted MCP server behind a Gateway:

```bash
agentcore gateway create-mcp-gateway --name RetailTherapyGateway
agentcore gateway create-mcp-gateway-target \
  --gateway-arn <gateway-arn-from-above> \
  --gateway-url <mcp-server-runtime-url-from-step-2> \
  --role-arn <execution-role-arn>
```
Then point `MCP_SERVER_URL` at the Gateway URL instead of the raw Runtime
endpoint — same tool contract, now discoverable/shareable across agents.

## 7. Wire up AgentCore Memory (production persistence)

Once you've verified the AgentCore Memory client methods against current
AWS docs (the preview SDK surface has been moving — see the note in
`src/memory_checkpointer.py`), create a memory resource and set
`AGENTCORE_MEMORY_ID` in the agent's Runtime env vars, then redeploy:

```bash
agentcore memory create --name RetailTherapyMemory
agentcore deploy   # re-deploy the agent with AGENTCORE_MEMORY_ID set
```

## Troubleshooting

| Issue | Fix |
|---|---|
| `No matching distribution found` on install | Python <3.10 — see the version-upgrade steps you already worked through earlier in this conversation |
| Agent can't reach MCP server | Confirm `MCP_SERVER_URL` includes the `?qualifier=DEFAULT` suffix and `MCP_BEARER_TOKEN` is set as a Runtime env var, not just locally in `.env` |
| HITL interrupt doesn't resume correctly | Make sure both calls use the same `session_id` — AgentCore Runtime session isolation means a different session_id looks like a brand new conversation |
| `AWS credentials are for account X, but target is configured for account Y` | See the account-mismatch fix from earlier — check `aws sts get-caller-identity` against `agentcore/aws-targets.json` |
