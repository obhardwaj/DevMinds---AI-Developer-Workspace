# backend/test_js_parser.py
# Throwaway check for JS/TS parsing + import-edge resolution.

import textwrap
from pathlib import Path

Path("test_js_app").mkdir(exist_ok=True)
Path("test_js_app/utils.js").write_text(textwrap.dedent("""
    /** Adds two numbers. */
    function add(a, b) {
        return a + b;
    }

    const subtract = (a, b) => a - b;

    module.exports = { add, subtract };
"""))
Path("test_js_app/index.js").write_text(textwrap.dedent("""
    const { add } = require('./utils');

    class Calculator {
        run() {
            return add(2, 3);
        }
    }
"""))

from app.engine.parser import parse_repository
from app.engine.graph_builder import build_dependency_edges

graph = build_dependency_edges(parse_repository("test_js_app"))
print(f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")
for node_id, node in graph.nodes.items():
    print(node.kind, node.name, "| docstring:", node.has_docstring)
for edge in graph.edges:
    print(edge.relation, edge.source_id, "->", edge.target_id)