# backend/app/engine/parser.py
# Uses Tree-sitter to turn source files into ASTs. This is the only
# place in the codebase that touches raw source text — everything
# downstream works with the structured graph instead.

from pathlib import Path
from app.engine.graph_models import CodeNode, RepoGraph


def parse_repository(repo_path: str) -> RepoGraph:
    """
    Walk every source file under `repo_path`, parse it with Tree-sitter,
    and return the raw list of discovered nodes (files/classes/functions)
    before dependency edges are added by graph_builder.py.

    TODO: dispatch to the correct Tree-sitter grammar per file extension
    (.py, .js, .ts, .java) and extract class/function boundaries from
    each AST.
    """
    graph = RepoGraph()
    for file_path in Path(repo_path).rglob("*.py"):
        node_id = str(file_path)
        graph.nodes[node_id] = CodeNode(
            id=node_id, kind="file", file_path=str(file_path),
            name=file_path.name, start_line=1, end_line=0,
        )
    return graph