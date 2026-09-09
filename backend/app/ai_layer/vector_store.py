# backend/app/ai_layer/vector_store.py
# Optional AI layer, step 2: stores/retrieves embeddings in ChromaDB
# so the RAG chat can pull relevant code chunks for a question.

import chromadb
from app.config import settings

_client = None


def get_client():
    global _client
    if _client is None:
        _client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
    return _client


def upsert_embeddings(repo_id: str, embedded_chunks: list[dict]) -> None:
    """TODO: write embedded_chunks into a Chroma collection named after repo_id."""
    pass


def retrieve_relevant_chunks(repo_id: str, query: str, top_k: int = 5) -> list[dict]:
    """TODO: embed `query` and return the top_k nearest chunks from Chroma."""
    return []
