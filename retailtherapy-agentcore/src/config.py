"""
Configuration, logging, and Amazon Bedrock model setup.
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
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0"
)

# MCP tool server location. Locally this is http://localhost:8000/mcp.
# In production this is the deployed AgentCore Runtime MCP endpoint.
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
MCP_BEARER_TOKEN = os.getenv("MCP_BEARER_TOKEN", "")

# AgentCore Memory (production checkpointer). Leave unset for local dev,
# which falls back to LangGraph's in-process MemorySaver.
AGENTCORE_MEMORY_ID = os.getenv("AGENTCORE_MEMORY_ID", "")


def get_chat_model():
    """Return the Amazon Bedrock chat model used by the application."""
    from langchain_aws import ChatBedrockConverse

    return ChatBedrockConverse(
        model=BEDROCK_MODEL_ID,
        region_name=AWS_REGION,
        temperature=0.2,
    )
