# backend/app/modules/health_index.py
# Repository Health Index: combines complexity, documentation, test
# coverage, security, and duplication signals into one 0-100 score.
# Reads only from the RepoGraph — no AI involved.

from app.engine.graph_models import RepoGraph

WEIGHTS = {
    "complexity": 0.25,
    "documentation": 0.20,
    "test_coverage": 0.20,
    "security": 0.20,
    "duplication": 0.15,
}


def compute_health_index(graph: RepoGraph) -> dict:
    """
    Returns something like:
    {"score": 78, "breakdown": {"complexity": 80, "documentation": 60, ...}}

    TODO: implement each sub-metric:
      - complexity: cyclomatic complexity per function, averaged
      - documentation: % of public functions/classes with docstrings
      - test_coverage: heuristic based on test-file-to-source-file ratio
      - security: count of known-risky patterns (e.g. eval, hardcoded secrets)
      - duplication: % of duplicated code blocks (see similarity.py logic)
    """
    breakdown = {k: 0 for k in WEIGHTS}
    score = sum(breakdown[k] * w for k, w in WEIGHTS.items())
    return {"score": round(score, 1), "breakdown": breakdown}
