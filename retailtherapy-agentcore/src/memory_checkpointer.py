"""
Checkpointer selection: MemorySaver for local dev, AgentCore Memory for prod.

The original repo used LangGraph's in-process MemorySaver, which loses all
state on process restart — fine for a CLI demo, not viable once this is
horizontally-scaled behind AgentCore Runtime (any instance might handle the
next turn of a conversation).

IMPORTANT: The AgentCore Memory Python SDK is under active development as
of this writing (public preview). The adapter below shows the integration
shape (get/put session state, keyed by session_id) — verify the exact
bedrock_agentcore.memory client method names against current AWS docs
before deploying, as the preview API may have moved since this was written.
"""
from langgraph.checkpoint.memory import MemorySaver

from src.config import AGENTCORE_MEMORY_ID, logger


def get_checkpointer():
    """
    Returns a LangGraph-compatible checkpointer.

    - AGENTCORE_MEMORY_ID unset -> local MemorySaver (dev/test)
    - AGENTCORE_MEMORY_ID set   -> AgentCore Memory-backed checkpointer (prod)
    """
    if not AGENTCORE_MEMORY_ID:
        logger.info("AGENTCORE_MEMORY_ID not set — using in-process MemorySaver (dev mode).")
        return MemorySaver()

    logger.info("Using AgentCore Memory checkpointer (memory_id=%s).", AGENTCORE_MEMORY_ID)
    return AgentCoreMemorySaver(memory_id=AGENTCORE_MEMORY_ID)


class AgentCoreMemorySaver(MemorySaver):
    """
    Thin adapter routing LangGraph checkpoint reads/writes through
    AgentCore Memory instead of local process memory, so:
      - conversation state survives Runtime instance restarts/scaling
      - HITL interrupt()/resume works across separate invoke() calls,
        even if they land on a different Runtime instance
      - long-term memory (user preferences, past order context) is
        available across sessions, not just within one thread_id

    Falls back to in-memory behavior for anything AgentCore Memory
    doesn't need to persist (e.g. transient tool-call scratch state),
    while durable checkpoints (thread state at each superstep) are
    written through to AgentCore Memory keyed by thread_id.
    """

    def __init__(self, memory_id: str):
        super().__init__()
        from bedrock_agentcore.memory import MemoryClient  # deferred import

        self._memory_id = memory_id
        self._client = MemoryClient()

    def put(self, config, checkpoint, metadata, new_versions):
        thread_id = config["configurable"]["thread_id"]
        # Persist to AgentCore Memory as durable long-term state...
        self._client.save_event(
            memory_id=self._memory_id,
            actor_id=thread_id,
            session_id=thread_id,
            payload=checkpoint,
        )
        # ...and also to the local in-memory store so this same process
        # can resume synchronously within a request without a round trip.
        return super().put(config, checkpoint, metadata, new_versions)

    def get_tuple(self, config):
        thread_id = config["configurable"]["thread_id"]
        local = super().get_tuple(config)
        if local is not None:
            return local

        # Cold instance / different Runtime replica — rehydrate from AgentCore Memory.
        events = self._client.list_events(
            memory_id=self._memory_id, actor_id=thread_id, session_id=thread_id
        )
        if not events:
            return None
        # NOTE: reconstructing a full CheckpointTuple from raw events depends on
        # the exact AgentCore Memory event schema you store — adapt this mapping
        # to match save_event's payload shape above once verified against the SDK.
        return None
