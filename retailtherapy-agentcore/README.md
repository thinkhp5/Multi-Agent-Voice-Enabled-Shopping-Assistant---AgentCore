# 🛒 RetailTherapy — Multi-Agent Voice-Enabled Shopping Assistant on Amazon Bedrock AgentCore

RetailTherapy is a **multi-agent AI shopping and customer-support assistant** built with **LangGraph, Amazon Bedrock, Amazon Bedrock AgentCore Runtime, and Model Context Protocol (MCP)**.

The system separates shopping and customer-support responsibilities into specialized agents. An LLM-powered orchestrator determines which specialist should handle a request, agents can execute in parallel, MCP provides a standardized tool interface, and a synthesizer combines multiple specialist responses into one natural answer.

The project also demonstrates **RAG, Human-in-the-Loop (HITL), conversation memory, tool calling, and voice-oriented components**.

---

## ✨ What This Project Demonstrates

This project is designed as a practical example of how to build and deploy a production-oriented multi-agent architecture on AWS.

### Core capabilities

* 🤖 **Multi-agent orchestration with LangGraph**
* 🛍️ **Product discovery agent**
* 🎧 **Customer-support/order agent**
* 🔀 **Dynamic routing based on user intent**
* ⚡ **Parallel agent execution**
* 🔌 **MCP-based tool integration**
* 🔎 **RAG-based product search**
* 📦 **Order-status lookup**
* 🙋 **Human-in-the-Loop interaction**
* 🧠 **Conversation state and memory**
* 🗣️ **Voice components**
* ☁️ **Amazon Bedrock AgentCore Runtime**
* 📊 **AgentCore observability**
* 🔐 **AWS IAM-based deployment and runtime access**

---

# 🏗️ Architecture

At a high level, the application follows this flow:

```text
                           ┌─────────────────────┐
                           │       User          │
                           │ Text / Voice Input  │
                           └──────────┬──────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │  AgentCore Runtime  │
                           │    runtime_app.py   │
                           └──────────┬──────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │     Orchestrator    │
                           │     LangGraph Node  │
                           └──────────┬──────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 │                 ▼
          ┌──────────────────┐       │       ┌──────────────────┐
          │  Product Agent   │       │       │  Support Agent   │
          │                  │       │       │                  │
          │ Product search   │       │       │ Order tracking   │
          │ Recommendations  │       │       │ Returns          │
          │ Catalog RAG      │       │       │ Escalation       │
          └────────┬─────────┘       │       └────────┬─────────┘
                   │                 │                │
                   └─────────────────┼────────────────┘
                                     │
                                     ▼
                           ┌─────────────────────┐
                           │     Synthesizer     │
                           │                     │
                           │ Combines specialist│
                           │ responses when     │
                           │ multiple agents run│
                           └──────────┬──────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │   Final Response    │
                           └─────────────────────┘
```

---

# 🧠 LangGraph Workflow

The main graph is defined in:

```text
src/graph.py
```

The graph contains four primary nodes:

```text
START
  │
  ▼
orchestrator
  │
  ├───────────────► product_agent ──────┐
  │                                     │
  └───────────────► support_agent ──────┤
                                        ▼
                                  synthesizer
                                        │
                                        ▼
                                       END
```

The orchestrator uses LangGraph's `Send()` mechanism to dynamically dispatch work.

For example:

### Product request

```text
"Find me wireless headphones under $200"
```

Routes to:

```text
product_agent
```

### Support request

```text
"Track my order ORD102"
```

Routes to:

```text
support_agent
```

### Mixed request

```text
"My order is late. Also show me alternatives to the headphones I bought."
```

Can route to both:

```text
product_agent
       +
support_agent
       ↓
  synthesizer
```

This allows independent work to execute in parallel before the final answer is composed.

---

# 🤖 The Agents

## 1. Orchestrator

The orchestrator is responsible for **intent classification and task routing**.

It determines whether the request requires:

* `product_agent`
* `support_agent`
* both agents

The orchestrator produces tasks containing:

```json
{
  "tasks": [
    {
      "agent": "support_agent",
      "instructions": "Find the current order status for the customer."
    }
  ]
}
```

The tasks are then converted into LangGraph `Send()` operations.

### Routing principle

```text
User request
     │
     ▼
Orchestrator
     │
     ├── Shopping/product → Product Agent
     │
     ├── Order/support   → Support Agent
     │
     └── Mixed request   → Both
```

The implementation also includes a deterministic fallback for obvious support intents such as:

* order
* tracking
* return
* refund
* cancellation
* shipment
* delivery

This prevents a malformed LLM classification response from silently routing a customer-support request to the product agent.

---

# 🛍️ 2. Product Agent

The product agent specializes in product discovery.

Its system prompt instructs it to use:

```text
search_product_catalog
```

The agent follows a model → tool → model loop:

```text
Product Agent
     │
     ▼
   LLM
     │
     ├── Tool call ──► MCP
     │                  │
     │                  ▼
     │             Product Search
     │
     └── Final answer
```

Typical requests:

```text
Find wireless headphones under $200.
```

```text
Show me alternatives to Sony headphones.
```

```text
What products do you have for travel?
```

---

# 🆘 3. Support Agent

The support agent handles customer-service workflows.

It has access to:

```text
get_order_status
escalate_to_human
```

Typical requests include:

* Order tracking
* Order status
* Returns
* Refunds
* Cancellations
* Delivery issues
* Human escalation

The support agent also demonstrates **Human-in-the-Loop** behavior.

If the agent needs additional information, the graph can pause using LangGraph's:

```python
interrupt()
```

The application returns an interruption response such as:

```json
{
  "status": "interrupted",
  "question": "Could you provide your order ID or email?",
  "session_id": "..."
}
```

The user can then provide the missing information and resume the graph.

---

# 🔌 Model Context Protocol (MCP)

MCP is used to separate **agent reasoning** from **tool implementation**.

Instead of embedding every backend operation directly into the agent, the agents discover and call tools through an MCP server.

The MCP server is implemented in:

```text
mcp_server/server.py
```

The current tool interface includes:

| MCP Tool                 | Purpose                    |
| ------------------------ | -------------------------- |
| `search_product_catalog` | Search the product catalog |
| `get_order_status`       | Retrieve order status      |
| `escalate_to_human`      | Escalate a customer issue  |

This architecture makes the tools independently discoverable and allows the same MCP interface to be used locally or through an AgentCore MCP runtime.

### Why MCP?

MCP provides a standardized boundary between:

```text
Agent reasoning
      │
      ▼
     MCP
      │
      ├── Product search
      ├── Order lookup
      └── Human escalation
```

This reduces tight coupling between the agent logic and backend tools.

It also makes it easier to add additional capabilities without rewriting the core orchestration graph.

---

# 🔎 RAG / Product Search

The product agent uses the product catalog through the RAG layer.

Relevant code:

```text
src/rag.py
src/data.py
```

The conceptual flow is:

```text
Product Catalog
      │
      ▼
Embeddings / Vector Store
      │
      ▼
Semantic Search
      │
      ▼
search_product_catalog
      │
      ▼
Product Agent
```

This allows users to search using natural language rather than requiring exact product names.

For example:

```text
"I need affordable headphones for travel with good battery life."
```

can be translated into a semantic catalog search.

---

# 🧠 Memory and Conversation State

The graph is compiled with a checkpointer:

```python
builder.compile(
    checkpointer=get_checkpointer()
)
```

For local development, the application uses an in-process memory implementation when:

```text
AGENTCORE_MEMORY_ID
```

is not configured.

When running with AgentCore-managed memory, the runtime can use an AgentCore Memory resource.

Each conversation is associated with a session/thread identifier:

```python
config = {
    "configurable": {
        "thread_id": session_id
    }
}
```

This is important for:

* Multi-turn conversations
* HITL interruptions
* Resume operations
* Maintaining conversational context

---

# 🙋 Human-in-the-Loop Flow

The support agent demonstrates a pause/resume workflow.

Example:

```text
User:
Track my order

       │
       ▼

Support Agent:
I need your order ID or email.

       │
       ▼

LangGraph interrupt()

       │
       ▼

User:
ORD102

       │
       ▼

Command(resume="ORD102")

       │
       ▼

Support Agent
       │
       ▼
get_order_status
       │
       ▼
Final Response
```

The key implementation is:

```python
interrupt(response.content)
```

and later:

```python
Command(resume=user_answer)
```

This allows the workflow to pause without losing its execution context.

---

# 🗣️ Voice

The project also contains voice-related functionality under:

```text
src/voice.py
```

The broader RetailTherapy architecture supports voice input/output around the same agent graph.

The AgentCore runtime entrypoint currently exposes a structured payload interface, allowing a client or voice layer to pass user requests into the graph.

The core agent logic therefore remains independent from the presentation channel:

```text
Text Client ──────┐
                  │
Voice Client ─────┼──► AgentCore Runtime
                  │          │
Other Client ─────┘          ▼
                         LangGraph
```

---

# 📁 Project Structure

```text
retailtherapy-agentcore/
│
├── runtime_app.py
│   └── AgentCore Runtime HTTP entrypoint
│
├── mcp_server/
│   ├── __init__.py
│   └── server.py
│       └── MCP server and tool definitions
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   │   └── AWS / model configuration
│   │
│   ├── data.py
│   │   └── Product and order data
│   │
│   ├── graph.py
│   │   └── LangGraph StateGraph
│   │
│   ├── mcp_tool_client.py
│   │   └── MCP client integration
│   │
│   ├── memory_checkpointer.py
│   │   └── Local / AgentCore memory integration
│   │
│   ├── nodes.py
│   │   ├── Orchestrator
│   │   ├── Product Agent
│   │   ├── Support Agent
│   │   └── Synthesizer
│   │
│   ├── rag.py
│   │   └── Product retrieval / RAG
│   │
│   ├── state.py
│   │   └── LangGraph state definitions
│   │
│   └── voice.py
│       └── Voice functionality
│
├── requirements.txt
├── requirements-mcp.txt
├── .env.example
├── .bedrock_agentcore.yaml
├── DEPLOY.md
└── README.md
```

---

# ⚙️ Prerequisites

## Required

* Python 3.12
* AWS CLI
* AWS credentials configured
* Amazon Bedrock model access
* Node.js/npm if using the current AgentCore CLI
* An AWS account with permissions to deploy AgentCore resources

The current AWS AgentCore CLI is distributed as:

```bash
npm install -g @aws/agentcore
```

AWS documents Python 3.12 as a supported AgentCore Runtime version.

Verify:

```bash
python --version
aws --version
node --version
npm --version
```

Verify AWS credentials:

```bash
aws sts get-caller-identity
```

---

# 🚀 Local Setup

Clone the repository:

```bash
git clone https://github.com/thinkhp5/Multi-Agent-Voice-Enabled-Shopping-Assistant---AgentCore.git
```

Change into the AgentCore application:

```bash
cd Multi-Agent-Voice-Enabled-Shopping-Assistant---AgentCore/retailtherapy-agentcore
```

Create a virtual environment:

```bash
python3.12 -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

For MCP-specific dependencies:

```bash
pip install -r requirements-mcp.txt
```

---

# 🔐 Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Configure the variables required by your environment.

For Bedrock model selection, the application reads:

```text
BEDROCK_MODEL_ID
```

For example:

```text
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

The exact model/inference profile available to your AWS account and region should be verified before use.

You can inspect available inference profiles with:

```bash
aws bedrock list-inference-profiles \
  --region us-east-1
```

> Do not commit `.env`, AWS credentials, access-key CSV files, or other secrets to GitHub.

---

# ▶️ Run the Application Locally

The simplest way to run the full LangGraph application locally is:

```bash
python runtime_app.py --local
```

You should see:

```text
RetailTherapy (local, AgentCore-shaped) — type 'quit' to exit
```

Then try:

```text
Find me wireless headphones under $200
```

The request should route to:

```text
orchestrator
    ↓
product_agent
    ↓
synthesizer
```

---

## Test Customer Support

Try:

```text
Track my order
```

The orchestrator should route the request to:

```text
support_agent
```

If the support agent requires additional information, the application will pause for a response.

For example:

```text
You: Track my order

Assistant asks:
Could you provide your order ID or email?

You: ORD102
```

The graph then resumes.

---

## Test Email-Based Order Lookup

Try:

```text
alex@example.com - find order status for this email
```

This should route to:

```text
support_agent
```

which can use:

```text
get_order_status
```

when the MCP tool schema supports the supplied customer identifier.

---

## Test Multi-Agent Routing

Try:

```text
My order ORD102 is delayed. Also show me alternatives to the product I purchased.
```

The orchestrator can dispatch:

```text
product_agent
       +
support_agent
       │
       ▼
  synthesizer
```

The synthesizer then combines the specialist responses.

---

# 🔌 Run the MCP Server Locally

The MCP server is a separate runtime component.

Run it with:

```bash
python -m mcp_server.server
```

Using the module form is important because the MCP server imports modules from the project's `src` package.

The local application communicates with the MCP endpoint through the configured MCP client.

A typical local flow is:

```text
runtime_app.py
      │
      ▼
LangGraph
      │
      ▼
Specialist Agent
      │
      ▼
MCP Client
      │
      ▼
MCP Server
      │
      ├── search_product_catalog
      ├── get_order_status
      └── escalate_to_human
```

---

# ☁️ Amazon Bedrock AgentCore

The project contains an AgentCore Runtime entrypoint:

```text
runtime_app.py
```

The entrypoint uses:

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp
```

and exposes:

```python
@app.entrypoint
async def invoke(payload: dict):
```

This makes the LangGraph application suitable for hosting in Amazon Bedrock AgentCore Runtime.

AgentCore Runtime supports direct code deployment for Python applications and packages the application and dependencies for managed runtime execution.

---

# 📦 AgentCore Configuration

AgentCore configuration is maintained through the project's AgentCore configuration files, including:

```text
.bedrock_agentcore.yaml
```

and AgentCore project configuration where applicable:

```text
agentcore/
```

The repository also contains deployment documentation in:

```text
DEPLOY.md
```

Before deploying, verify:

```bash
agentcore --help
```

and:

```bash
agentcore status
```

The current AWS AgentCore CLI uses commands such as:

```bash
agentcore deploy
agentcore status
agentcore invoke
```

AWS's current documentation recommends the npm-distributed AgentCore CLI:

```bash
npm install -g @aws/agentcore
```

and deployment through:

```bash
agentcore deploy
```

> **Important:** The repository may contain configuration generated by an earlier AgentCore toolkit version. If your local CLI reports that the project is not a recognized AgentCore CLI project, do not recreate or import the project blindly. Inspect the existing `agentcore/` configuration and follow the migration path appropriate for the installed CLI.

---

# 🧪 AgentCore Deployment

For a project recognized by the current AgentCore CLI:

```bash
agentcore deploy
```

Check deployment status:

```bash
agentcore status
```

AWS also supports deployment preview using:

```bash
agentcore deploy --dry-run
```

After deployment, invoke the runtime using the syntax supported by your installed CLI. Current AgentCore documentation uses:

```bash
agentcore invoke "Find me wireless headphones under $200"
```

---

# 🔍 Observability

AgentCore Runtime can integrate runtime logging and observability with AWS services.

This project enables observability through its AgentCore configuration.

Useful commands include:

```bash
agentcore logs
```

and:

```bash
agentcore traces
```

depending on the installed CLI version and configured observability resources.

CloudWatch can also be used to inspect runtime logs and deployment failures.

---

# 🔐 IAM Considerations

AgentCore deployment requires AWS permissions for the resources being provisioned.

Typical areas include:

```text
Amazon Bedrock
Amazon Bedrock AgentCore
AWS CloudFormation
AWS CDK bootstrap resources
Amazon S3
AWS IAM
CloudWatch Logs
AWS Systems Manager Parameter Store
```

The runtime execution role also needs permissions appropriate for:

* invoking the selected Bedrock model/inference profile
* accessing AgentCore resources
* accessing MCP-backed services
* writing observability data where enabled

Follow the principle of least privilege.

Avoid granting:

```text
AdministratorAccess
```

or unrestricted:

```text
s3:*
iam:*
```

unless there is a specific, documented requirement.

---

# 🧩 Model Configuration

The project uses Amazon Bedrock through LangChain's Bedrock Converse integration.

The model is configured in:

```text
src/config.py
```

The configuration reads:

```python
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID",
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)
```

For models that require inference profiles, use the appropriate inference-profile identifier rather than an unsupported direct foundation-model ID.

You can inspect available profiles with:

```bash
aws bedrock list-inference-profiles \
  --region us-east-1
```

---

# 🛠️ Troubleshooting

## `ModuleNotFoundError: No module named 'src'`

Run the MCP server from the project root using:

```bash
python -m mcp_server.server
```

instead of:

```bash
python mcp_server/server.py
```

---

## Orchestrator always routes to product_agent

Check the logs for:

```text
Orchestrator classification failed
```

The orchestrator should log the raw classification and selected route.

Expected examples:

```text
Orchestrator routing: ['product_agent']
```

or:

```text
Orchestrator routing: ['support_agent']
```

or:

```text
Orchestrator routing: ['product_agent', 'support_agent']
```

If support requests are being routed to the product agent, inspect:

```text
src/nodes.py
```

especially:

```python
orchestrator_node()
```

---

## Bedrock model invocation error

If Bedrock reports that a model does not support on-demand invocation, use an inference profile that contains the selected model.

Check:

```bash
aws bedrock list-inference-profiles \
  --region us-east-1
```

Then test the selected profile directly before testing the complete graph.

---

## `AccessDeniedException`

Do not immediately grant broad permissions.

Read the exact AWS error and identify the missing action.

Examples may include:

```text
bedrock:InvokeModel
bedrock:ListInferenceProfiles
logs:PutDeliverySource
iam:PassRole
```

Grant only the required action and scope it to the appropriate resource whenever AWS supports resource-level permissions.

---

## AgentCore deployment fails during CDK bootstrap

AgentCore deployment uses AWS CDK infrastructure under the hood. AWS documents that the CLI may bootstrap the account and provision resources during deployment.

Check:

```bash
aws cloudformation describe-stacks \
  --stack-name CDKToolkit \
  --region us-east-1
```

Also inspect the AgentCore deployment output and CloudFormation events.

---

# 🧱 Design Principles

This project intentionally separates concerns.

### Agent reasoning

```text
LangGraph
```

handles:

* orchestration
* state
* routing
* parallelism
* HITL
* synthesis

### Tool interface

```text
MCP
```

handles:

* product search
* order lookup
* escalation

### Model layer

```text
Amazon Bedrock
```

handles:

* classification
* reasoning
* tool selection
* response generation
* synthesis

### Runtime layer

```text
Amazon Bedrock AgentCore Runtime
```

handles:

* managed execution
* runtime lifecycle
* deployment
* scaling
* observability

This separation makes the architecture easier to extend and deploy.

---

# 🔄 End-to-End Request Flow

For a simple product request:

```text
User
 │
 ▼
AgentCore Runtime
 │
 ▼
LangGraph Orchestrator
 │
 ▼
Product Agent
 │
 ▼
MCP Client
 │
 ▼
search_product_catalog
 │
 ▼
Product Agent
 │
 ▼
Synthesizer
 │
 ▼
User
```

For an order-support request:

```text
User
 │
 ▼
AgentCore Runtime
 │
 ▼
Orchestrator
 │
 ▼
Support Agent
 │
 ├── get_order_status
 │
 └── escalate_to_human
 │
 ▼
Final Response
```

For a mixed request:

```text
                 ┌── Product Agent ──► MCP
                 │
User ─► Orchestrator
                 │
                 └── Support Agent ─► MCP
                          │
                          ▼
                     Synthesizer
                          │
                          ▼
                         User
```

---

# 📈 Extending the System

The architecture is designed to support additional specialist agents.

For example:

```text
                    ┌── Product Agent
                    │
                    ├── Support Agent
                    │
Orchestrator ───────┼── Recommendation Agent
                    │
                    ├── Payments Agent
                    │
                    └── Returns Agent
```

A new specialist can be added by:

1. Defining the agent node.
2. Adding its tools.
3. Registering its node in the LangGraph.
4. Updating the orchestrator routing policy.
5. Adding or extending MCP tools.
6. Adding tests for routing and tool execution.

---

# 🧪 Example Scenarios

## Product Discovery

**User**

```text
Find me wireless headphones under $200.
```

**Flow**

```text
orchestrator
     ↓
product_agent
     ↓
search_product_catalog
     ↓
response
```

---

## Order Tracking

**User**

```text
Track my order.
```

**Flow**

```text
orchestrator
     ↓
support_agent
     ↓
HITL if order ID/email is missing
     ↓
get_order_status
     ↓
response
```

---

## Mixed Request

**User**

```text
My order is delayed. Find me another pair of headphones like the one I bought.
```

**Flow**

```text
                ┌── product_agent ──► product search
                │
orchestrator ───┤
                │
                └── support_agent ──► order status
                         │
                         ▼
                    synthesizer
                         │
                         ▼
                      response
```

---

# 🔒 Security Considerations

For production deployment, consider:

* Least-privilege IAM roles
* Short-lived credentials
* Explicit authorization at tool boundaries
* Input validation for tool parameters
* Tenant isolation if supporting multiple customers
* Authentication before accessing customer order information
* Audit logging
* CloudWatch observability
* Secrets stored outside source control
* Rate limiting
* Human approval for sensitive/destructive actions
* Validation that customer identity comes from the authenticated session rather than model-generated parameters

In particular, **customer email/order identifiers should not be trusted simply because the LLM generated them**. Production systems should bind customer identity to an authenticated session and enforce authorization at the tool/backend layer.

---

# 🚧 Current Scope

This repository is primarily a demonstration of:

```text
Multi-agent orchestration
+
LangGraph
+
Amazon Bedrock
+
MCP
+
RAG
+
HITL
+
AgentCore Runtime
```

The product and order data used by the project are demonstration data rather than a production e-commerce backend.

A production implementation would replace these components with authenticated services such as:

```text
Product Catalog Service
Order Management System
Customer Identity Provider
Support/Ticketing System
Payment Service
Inventory Service
```

while retaining the same high-level agent architecture.

---

# 🗺️ Roadmap

Potential future enhancements include:

* [ ] AgentCore Memory for long-term customer context
* [ ] Production product/vector database
* [ ] Real order-management API integration
* [ ] Authentication and customer identity propagation
* [ ] Stronger authorization at MCP/tool boundaries
* [ ] Streaming responses
* [ ] Production voice interface
* [ ] Automated evaluation of agent routing
* [ ] AgentCore Evaluations integration
* [ ] Additional specialist agents
* [ ] CI/CD deployment pipeline
* [ ] Automated security testing
* [ ] Guardrails for sensitive customer operations

---

# 📚 Key Technologies

| Technology                           | Role                                     |
| ------------------------------------ | ---------------------------------------- |
| **Amazon Bedrock**                   | Foundation models                        |
| **Amazon Bedrock AgentCore Runtime** | Managed agent runtime                    |
| **LangGraph**                        | Agent orchestration and state management |
| **LangChain**                        | LLM/tool integration                     |
| **MCP**                              | Standardized agent-tool communication    |
| **Python**                           | Application implementation               |
| **RAG**                              | Semantic product retrieval               |
| **AWS IAM**                          | Authentication and authorization         |
| **CloudWatch**                       | Logging and observability                |

---

# 📖 AWS Resources

* [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)
* [AgentCore Runtime documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy-python.html)
* [AgentCore CLI documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html)
* [Model Context Protocol](https://modelcontextprotocol.io/)
* [LangGraph documentation](https://langchain-ai.github.io/langgraph/)

AWS's current direct-code deployment documentation describes AgentCore Runtime as supporting Python entrypoints using `BedrockAgentCoreApp` and managed deployment through the AgentCore CLI.

---

# 👤 Author

**Swati Priya**

GitHub:

https://github.com/thinkhp5

Project:

https://github.com/thinkhp5/Multi-Agent-Voice-Enabled-Shopping-Assistant---AgentCore

---

## ⭐ Why This Project Matters

RetailTherapy demonstrates a practical approach to building AI applications where a single LLM is not responsible for everything.

Instead:

```text
                    ┌─────────────────┐
                    │   Orchestrator  │
                    └────────┬────────┘
                             │
             ┌───────────────┼───────────────┐
             ▼               ▼               ▼
        Product Agent   Support Agent    Future Agents
             │               │
             └───────┬───────┘
                     ▼
                   MCP
                     │
                     ▼
              Backend Tools
                     │
                     ▼
                 Synthesizer
                     │
                     ▼
                  Customer
```

The result is a modular architecture where **agents, tools, models, memory, and runtime infrastructure have clear responsibilities and boundaries**.

That makes the system easier to extend from a demonstration application toward a production-grade agent platform.

