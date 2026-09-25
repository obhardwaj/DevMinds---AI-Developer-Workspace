# backend/app/engine/parser.py
# Uses Tree-sitter to turn source files into ASTs and extract file,
# class, and function nodes into the RepoGraph. This is the only
# place in the codebase that touches raw source text — everything
# downstream (health index, pattern detector, etc.) works with the
# structured graph instead.
#
# Supports Python, JavaScript, JSX, TypeScript, and TSX. Each language
# is grouped into a "family" (python | javascript) because languages in
# the same family share enough AST shape to reuse one walker — Python's
# def/class syntax is unlike anything else here, while JS/JSX/TS/TSX are
# close enough (function_declaration, class_declaration, arrow functions)
# to share one walker.

import os
from pathlib import Path
from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript

from app.engine.graph_models import CodeNode, RepoGraph

PY_LANGUAGE = Language(tspython.language())
JS_LANGUAGE = Language(tsjavascript.language())
TS_LANGUAGE = Language(tstypescript.language_typescript())
TSX_LANGUAGE = Language(tstypescript.language_tsx())

EXTENSION_LANGUAGE_MAP = {
    ".py": PY_LANGUAGE,
    ".js": JS_LANGUAGE,
    ".jsx": JS_LANGUAGE,
    ".ts": TS_LANGUAGE,
    ".tsx": TSX_LANGUAGE,
    # TODO: ".java": JAVA_LANGUAGE
}

# Which walker + docstring convention applies to each extension.
LANGUAGE_FAMILY = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
}

EXCLUDED_DIRS = {
    "venv", ".venv", "env", "node_modules", ".git", "__pycache__",
    "site-packages", "dist", "build", ".mypy_cache", ".pytest_cache",
    "migrations",
}

# Statement-level node types in JS/TS whose PRECEDING SIBLING might be a
# JSDoc comment. Used to approximate "has documentation" the way Python's
# docstring check does — JS has no language-level docstring, so a leading
# /** ... */ comment is the closest equivalent convention.
JS_STATEMENT_TYPES = {
    "lexical_declaration", "variable_declaration", "function_declaration",
    "class_declaration", "method_definition",
}


def _get_text(source_bytes: bytes, node) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8")


def _walk_source_files(repo_path: str):
    """Yields Path objects for every source file under repo_path,
    skipping EXCLUDED_DIRS entirely (not just filtering results after)."""
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for filename in filenames:
            ext = Path(filename).suffix
            if ext in EXTENSION_LANGUAGE_MAP:
                yield Path(dirpath) / filename


# ---------- Python ----------

def _has_python_docstring(def_node) -> bool:
    """True if a function/class def's first statement is a bare string
    literal (Python's docstring convention)."""
    body = def_node.child_by_field_name("body")
    if not body or not body.children:
        return False
    first_stmt = body.children[0]
    return (
        first_stmt.type == "expression_statement"
        and len(first_stmt.children) > 0
        and first_stmt.children[0].type == "string"
    )


def _walk_python(node, source_bytes, file_path, graph):
    if node.type in ("function_definition", "class_definition"):
        name_node = node.child_by_field_name("name")
        name = _get_text(source_bytes, name_node) if name_node else "<anonymous>"
        kind = "function" if node.type == "function_definition" else "class"
        node_id = f"{file_path}::{name}"
        graph.nodes[node_id] = CodeNode(
            id=node_id, kind=kind, file_path=str(file_path), name=name,
            start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
            has_docstring=_has_python_docstring(node),
        )
    for child in node.children:
        _walk_python(child, source_bytes, file_path, graph)


# ---------- JavaScript / JSX / TypeScript / TSX ----------

def _nearest_js_statement(node):
    """Climbs from a function/class/arrow-function node to the nearest
    enclosing statement (and out through `export ...` if present), since
    a leading JSDoc comment attaches before the STATEMENT, not necessarily
    before the function/class node itself."""
    current = node
    while current is not None and current.type not in JS_STATEMENT_TYPES:
        current = current.parent
    if current is None:
        return node
    if current.parent is not None and current.parent.type == "export_statement":
        return current.parent
    return current


def _has_leading_jsdoc(node, source_bytes: bytes) -> bool:
    stmt = _nearest_js_statement(node)
    prev = stmt.prev_sibling
    if prev is not None and prev.type == "comment":
        return _get_text(source_bytes, prev).startswith("/**")
    return False


def _walk_javascript_family(node, source_bytes, file_path, graph):
    if node.type in ("function_declaration", "class_declaration", "method_definition"):
        name_node = node.child_by_field_name("name")
        name = _get_text(source_bytes, name_node) if name_node else "<anonymous>"
        kind = "class" if node.type == "class_declaration" else "function"
        node_id = f"{file_path}::{name}"
        graph.nodes[node_id] = CodeNode(
            id=node_id, kind=kind, file_path=str(file_path), name=name,
            start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
            has_docstring=_has_leading_jsdoc(node, source_bytes),
        )
    elif node.type == "variable_declarator":
        # Covers `const foo = () => {...}` and `const foo = function() {...}`
        value_node = node.child_by_field_name("value")
        name_node = node.child_by_field_name("name")
        if (
            value_node is not None and name_node is not None
            and value_node.type in ("arrow_function", "function_expression")
        ):
            name = _get_text(source_bytes, name_node)
            node_id = f"{file_path}::{name}"
            graph.nodes[node_id] = CodeNode(
                id=node_id, kind="function", file_path=str(file_path), name=name,
                start_line=value_node.start_point[0] + 1, end_line=value_node.end_point[0] + 1,
                has_docstring=_has_leading_jsdoc(node, source_bytes),
            )
    for child in node.children:
        _walk_javascript_family(child, source_bytes, file_path, graph)


WALKERS = {
    "python": _walk_python,
    "javascript": _walk_javascript_family,
}


def _extract_nodes_from_file(file_path: Path, graph: RepoGraph) -> None:
    """Parse one file and add its file/class/function nodes to `graph`."""
    language = EXTENSION_LANGUAGE_MAP.get(file_path.suffix)
    family = LANGUAGE_FAMILY.get(file_path.suffix)
    if language is None or family is None:
        return

    source_bytes = file_path.read_bytes()
    parser = Parser(language)
    tree = parser.parse(source_bytes)
    root = tree.root_node

    file_node_id = str(file_path)
    graph.nodes[file_node_id] = CodeNode(
        id=file_node_id, kind="file", file_path=str(file_path),
        name=file_path.name,
        start_line=root.start_point[0] + 1,
        end_line=root.end_point[0] + 1,
    )

    WALKERS[family](root, source_bytes, file_path, graph)


def parse_repository(repo_path: str) -> RepoGraph:
    """
    Walk every source file under `repo_path` (excluding dependency/build/
    VCS directories — see EXCLUDED_DIRS), parse it with Tree-sitter, and
    record a node for the file plus one node per class/function inside it.

    Dependency edges (imports/calls) are added next, by graph_builder.py.
    """
    graph = RepoGraph()
    for file_path in _walk_source_files(repo_path):
        _extract_nodes_from_file(file_path, graph)
    return graph