# backend/app/engine/graph_builder.py
# Takes the raw parsed nodes from parser.py and adds the dependency
# edges (imports, calls, inheritance) that turn a flat list of nodes
# into the graph every module actually reasons over.

from app.engine.graph_models import RepoGraph, CodeEdge


def build_dependency_edges(graph: RepoGraph) -> RepoGraph:
    """
    Populate graph.edges by resolving imports/calls/inheritance between
    the nodes already discovered by parser.py.

    TODO: for each file/class/function node, inspect its AST (kept
    alongside the node during parsing) to find import statements and
    call expressions, then resolve them to other node ids in this graph.
    """
    # Placeholder — real implementation walks each node's AST.
    return graph
