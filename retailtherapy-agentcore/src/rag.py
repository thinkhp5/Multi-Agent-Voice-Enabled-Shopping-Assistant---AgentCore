"""
Vector store for product catalog semantic search.

Lives on the MCP server side now (not the agent side) — the agent no
longer needs to know how product search is implemented, only that a
`search_product_catalog` tool exists.
"""
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore

from src.config import AWS_REGION, MODEL_PROVIDER
from src.data import PRODUCT_CATALOG

_vector_store = None


def _get_embeddings():
    if MODEL_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model="text-embedding-3-small")

    from langchain_aws import BedrockEmbeddings

    return BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v2:0", region_name=AWS_REGION
    )


def get_vector_store() -> InMemoryVectorStore:
    """Lazily build (once) and return the product catalog vector store."""
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    docs = [
        Document(
            page_content=f"{p['name']} — {p['description']} (${p['price']})",
            metadata=p,
        )
        for p in PRODUCT_CATALOG
    ]
    _vector_store = InMemoryVectorStore.from_documents(docs, _get_embeddings())
    return _vector_store


def search_products(query: str, k: int = 3) -> list[dict]:
    store = get_vector_store()
    results = store.similarity_search(query, k=k)
    return [r.metadata for r in results]
