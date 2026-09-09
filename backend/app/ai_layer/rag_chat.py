# backend/app/ai_layer/rag_chat.py
# Optional AI layer, step 3: answers a developer's natural-language
# question by retrieving relevant chunks and grounding an LLM's
# response in them (Retrieval-Augmented Generation).

from app.ai_layer.vector_store import retrieve_relevant_chunks
from app.config import settings


def answer_question(repo_id: str, question: str) -> str:
    """
    TODO:
      1. Guard: if not settings.AI_LAYER_ENABLED, return a message saying
         the AI layer is disabled and results come from modules directly.
      2. retrieve_relevant_chunks(repo_id, question)
      3. Build a prompt with those chunks + question, call the configured
         LLM_PROVIDER, and return its response.
    """
    if not settings.AI_LAYER_ENABLED:
        return "AI layer is disabled. Enable AI_LAYER_ENABLED to use chat."
    chunks = retrieve_relevant_chunks(repo_id, question)
    return "TODO: LLM response grounded in retrieved chunks"
