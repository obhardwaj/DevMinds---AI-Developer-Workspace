# backend/app/ai_layer/embeddings.py
# Optional AI layer, step 1: turns graph nodes into embeddable text
# chunks and calls a Sentence Transformer model to embed them.
# Only used if AI_LAYER_ENABLED=true.

from sentence_transformers import SentenceTransformer
from app.engine.graph_models import RepoGraph

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_graph(graph: RepoGraph) -> list[dict]:
    """
    Returns [{"node_id": ..., "embedding": [...]}] for every node.
    TODO: convert each CodeNode into a natural-language chunk
    (e.g. "function parse_file in src/utils/parser.py") before embedding.
    """
    return []
