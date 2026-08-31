"""
Config, logging, and model client setup.

Defaults to Amazon Bedrock (Claude) via langchain_aws so the whole stack
stays AWS-native alongside AgentCore. Set MODEL_PROVIDER=openai in .env
if you'd rather keep the original OpenAI models.
"""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("retailtherapy")

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "bedrock")  # "bedrock" | "openai"
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0"
)
OPENAI_MODEL_ID = os.getenv("OPENAI_MODEL_ID", "gpt-4o")

# MCP tool server location. Locally this is http://localhost:8000/mcp.
# In production this is the deployed AgentCore Runtime MCP endpoint
# (see DEPLOY.md for how to obtain this URL + bearer token).
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
MCP_BEARER_TOKEN = os.getenv("MCP_BEARER_TOKEN", "")

# AgentCore Memory (production checkpointer). Leave unset for local dev,
# which falls back to LangGraph's in-process MemorySaver.
AGENTCORE_MEMORY_ID = os.getenv("AGENTCORE_MEMORY_ID", "")


def get_chat_model():
    """Return a LangChain chat model, provider selected via MODEL_PROVIDER."""
    if MODEL_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=OPENAI_MODEL_ID, temperature=0.2)

    from langchain_aws import ChatBedrockConverse

    return ChatBedrockConverse(
        model=BEDROCK_MODEL_ID,
        region_name=AWS_REGION,
        temperature=0.2,
    )
