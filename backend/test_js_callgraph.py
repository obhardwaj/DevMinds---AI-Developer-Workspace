# backend/test_js_callgraph.py
# Throwaway check for JS call-graph resolution: same-file, named import,
# default import, and namespace-object member call.

import textwrap
from pathlib import Path

Path("test_js_app2").mkdir(exist_ok=True)
Path("test_js_app2/utils.js").write_text(textwrap.dedent("""
    function add(a, b) {
        return a + b;
    }
    function subtract(a, b) {
        return a - b;
    }
    module.exports = { add, subtract };
"""))
Path("test_js_app2/mathDefault.js").write_text(textwrap.dedent("""
    function square(x) {
        return x * x;
    }
    module.exports = square;
"""))
Path("test_js_app2/index.js").write_text(textwrap.dedent("""
    const { add } = require('./utils');
    const utils = require('./utils');
    const square = require('./mathDefault');

    function run() {
        add(1, 2);
        utils.subtract(5, 2);
        square(4);
    }
"""))

from app.engine.parser import parse_repository
from app.engine.graph_builder import build_dependency_edges

graph = build_dependency_edges(parse_repository("test_js_app2"))
print(f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")
for edge in graph.edges:
    if edge.relation == "calls":
        print(edge.relation, edge.source_id, "->", edge.target_id)