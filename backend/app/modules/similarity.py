# backend/app/modules/similarity.py
# Repository Similarity Algorithm: extracts a weighted feature vector
# per repository (folder structure, dependencies, detected patterns,
# metrics) and scores how alike two repositories are.

from app.engine.graph_models import RepoGraph

FEATURE_WEIGHTS = {
    "folder_structure": 0.25,
    "dependency_profile": 0.30,
    "design_patterns": 0.20,
    "software_metrics": 0.25,
}


def extract_features(graph: RepoGraph) -> dict:
    """Builds this repository's feature vector for comparison."""
    return {k: None for k in FEATURE_WEIGHTS}  # TODO: real extraction


def compute_similarity(graph_a: RepoGraph, graph_b: RepoGraph) -> float:
    """
    Returns a 0-1 similarity score between two repositories.

    TODO: extract_features() for both, compare each feature group
    (e.g. cosine similarity on dependency profiles, Jaccard on
    detected-pattern sets), then combine with FEATURE_WEIGHTS.
    """
    return 0.0
