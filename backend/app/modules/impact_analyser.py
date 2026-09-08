# backend/app/modules/impact_analyzer.py
# Impact Analyzer: given a proposed change to a file/class/function,
# traverses the dependency graph to predict what else it could break —
# before the change is actually made.

from app.engine.graph_models import RepoGraph


def analyze_impact(graph: RepoGraph, changed_node_id: str) -> list[str]:
    """
    Returns the list of node ids that transitively depend on
    `changed_node_id` (i.e. would be affected by changing it).

    TODO: reverse-BFS over graph.edges starting from changed_node_id,
    following edges backwards (who imports/calls this node), up to a
    configurable depth to avoid over-reporting on huge repos.
    """
    if changed_node_id not in graph.nodes:
        raise ValueError(f"Unknown node: {changed_node_id}")
    return []