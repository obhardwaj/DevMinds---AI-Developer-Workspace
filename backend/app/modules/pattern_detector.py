# backend/app/modules/pattern_detector.py
# Design Pattern Detector: rule-based structural matching over the
# class/inheritance graph to identify Singleton, Factory, Observer,
# Strategy, and MVC — no learned model, per Tsantalis et al.'s
# similarity-scoring approach to pattern detection.

from app.engine.graph_models import RepoGraph

KNOWN_PATTERNS = ["Singleton", "Factory", "Observer", "Strategy", "MVC"]


def detect_patterns(graph: RepoGraph) -> list[dict]:
    """
    Returns a list like:
    [{"pattern": "Singleton", "location": "src/db/connection.py::DBConnection",
      "reason": "single private constructor + static instance accessor"}]

    TODO: implement one structural rule per pattern in KNOWN_PATTERNS,
    each rule inspecting graph.nodes/graph.edges for the shape that
    pattern implies (e.g. Singleton -> private constructor + static getInstance).
    """
    return []
