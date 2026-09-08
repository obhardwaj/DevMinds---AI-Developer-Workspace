# backend/app/modules/dead_code.py
# Dead Code Detection: call-graph reachability analysis from every
# public entry point. Anything never reached is reported as a
# candidate for safe removal.

from app.engine.graph_models import RepoGraph


def find_dead_code(graph: RepoGraph, entry_points: list[str] | None = None) -> list[str]:
    """
    Returns a list of node ids (functions/classes/files) that are
    never reached from any entry point.

    TODO:
      1. If entry_points is None, auto-detect them (e.g. main(), route
         handlers, exported symbols).
      2. BFS/DFS over graph.edges (the "calls"/"imports" relations)
         starting from entry_points.
      3. Anything in graph.nodes not visited is dead code.
    """
    reached: set[str] = set()
    return [node_id for node_id in graph.nodes if node_id not in reached]