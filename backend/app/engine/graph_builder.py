# backend/app/engine/graph_builder.py
# Takes the nodes discovered by parser.py and adds dependency edges.
#
# Python: file->file "imports" edges, function->function "calls" edges
# (same-file and cross-file via resolved imports), plus any framework
# "includes" edges from engine/conventions/ (Django, Flask so far).
#
# JavaScript/TypeScript: file->file "imports" edges only, for both ES
# module imports (`import x from './y'`) and CommonJS (`require('./y')`).
# Call-graph resolution for JS/TS is NOT done yet — its module system
# (default vs named exports, re-exports, ESM/CommonJS interop) needs its
# own resolver rather than reusing Python's, and is a clear next step
# rather than a gap papered over with guesses.
#
# Framework conventions (engine/conventions/) currently only implement
# Python frameworks (Django, Flask), so convention edges are only
# extracted for Python files — a JS convention plugin (e.g. Express) is
# a natural addition once one is written.

import os
from pathlib import Path
from tree_sitter import Parser
from app.engine.parser import EXTENSION_LANGUAGE_MAP, LANGUAGE_FAMILY
from app.engine.graph_models import RepoGraph, CodeEdge
from app.engine.conventions.registry import detect_conventions


def _get_text(source_bytes: bytes, node) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8")


# ---------- Python: import + call extraction (unchanged from before) ----------

def _extract_import_bindings(root, source_bytes: bytes) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    module_aliases: dict[str, str] = {}
    symbol_aliases: dict[str, tuple[str, str]] = {}

    def walk(node):
        if node.type == "import_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    dotted = _get_text(source_bytes, child)
                    module_aliases[dotted.split(".")[0]] = dotted
                elif child.type == "aliased_import":
                    name_node = child.child_by_field_name("name")
                    alias_node = child.child_by_field_name("alias")
                    if name_node and alias_node:
                        module_aliases[_get_text(source_bytes, alias_node)] = _get_text(source_bytes, name_node)
        elif node.type == "import_from_statement":
            module_node = node.child_by_field_name("module_name")
            module_name = _get_text(source_bytes, module_node) if module_node else ""
            for child in node.children:
                if child.type == "dotted_name" and child != module_node:
                    original = _get_text(source_bytes, child)
                    symbol_aliases[original] = (module_name, original)
                elif child.type == "aliased_import":
                    name_node = child.child_by_field_name("name")
                    alias_node = child.child_by_field_name("alias")
                    if name_node and alias_node:
                        original = _get_text(source_bytes, name_node)
                        symbol_aliases[_get_text(source_bytes, alias_node)] = (module_name, original)
        for child in node.children:
            walk(child)

    walk(root)
    return module_aliases, symbol_aliases


def _extract_python_imports(root, source_bytes: bytes) -> list[str]:
    imports = []

    def walk(node):
        if node.type == "import_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    imports.append(_get_text(source_bytes, child))
        elif node.type == "import_from_statement":
            module_node = node.child_by_field_name("module_name")
            if module_node:
                imports.append(_get_text(source_bytes, module_node))
        for child in node.children:
            walk(child)

    walk(root)
    return imports


def _extract_call_sites(root, source_bytes: bytes) -> list[dict]:
    calls = []

    def walk(node, current_function: str):
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            current_function = _get_text(source_bytes, name_node) if name_node else current_function
        if node.type == "call":
            func_node = node.child_by_field_name("function")
            if func_node:
                if func_node.type == "identifier":
                    calls.append({"caller": current_function, "kind": "identifier",
                                  "name": _get_text(source_bytes, func_node), "object": None})
                elif func_node.type == "attribute":
                    obj_node = func_node.child_by_field_name("object")
                    attr_node = func_node.child_by_field_name("attribute")
                    if obj_node and attr_node and obj_node.type == "identifier":
                        calls.append({"caller": current_function, "kind": "attribute",
                                      "name": _get_text(source_bytes, attr_node),
                                      "object": _get_text(source_bytes, obj_node)})
                    else:
                        calls.append({"caller": current_function, "kind": "other", "name": None, "object": None})
        for child in node.children:
            walk(child, current_function)

    walk(root, current_function="")
    return calls


def _module_name_to_file_id(module_name: str, graph: RepoGraph) -> str | None:
    target_suffix = module_name.replace(".", "/") + ".py"
    for node_id, node in graph.nodes.items():
        if node.kind == "file" and node.file_path.replace("\\", "/").endswith(target_suffix):
            return node_id
    return None


# ---------- JavaScript/TypeScript: import extraction (new) ----------

def _extract_js_imports(root, source_bytes: bytes) -> list[str]:
    """
    Returns raw import specifiers from ES module imports and CommonJS
    require() calls, e.g. ['./utils/helper', 'express', '../models/user'].
    Bare package names (no leading '.') are collected too but simply won't
    resolve to any graph node later — correctly, since they point outside
    the repo (node_modules), same as an unresolved Python import.
    """
    specifiers = []

    def walk(node):
        if node.type == "import_statement":
            source_node = node.child_by_field_name("source")
            if source_node is not None:
                specifiers.append(_get_text(source_bytes, source_node).strip("'\""))
        elif node.type == "call_expression":
            func_node = node.child_by_field_name("function")
            if func_node is not None and func_node.type == "identifier" and _get_text(source_bytes, func_node) == "require":
                args_node = node.child_by_field_name("arguments")
                for child in (args_node.children if args_node else []):
                    if child.type == "string":
                        specifiers.append(_get_text(source_bytes, child).strip("'\""))
                        break
        for child in node.children:
            walk(child)

    walk(root)
    return specifiers


def _resolve_js_relative_import(importing_path: Path, specifier: str, graph: RepoGraph) -> str | None:
    """
    Resolves a relative JS/TS specifier (e.g. './utils/helper') to a file
    node id already in the graph, trying common extensions and index-file
    conventions. Bare package specifiers (no leading '.') are never
    resolved — they point to node_modules, outside the repo.
    Best-effort: doesn't yet handle package.json "main"/"exports" fields
    or tsconfig path aliases.
    """
    if not specifier.startswith("."):
        return None

    base = Path(os.path.normpath(importing_path.parent / specifier))
    candidates = [base]
    if base.suffix == "":
        candidates += [
            base.with_suffix(".js"), base.with_suffix(".jsx"),
            base.with_suffix(".ts"), base.with_suffix(".tsx"),
            base / "index.js", base / "index.ts",
        ]
    for candidate in candidates:
        if str(candidate) in graph.nodes:
            return str(candidate)
    return None


def build_dependency_edges(graph: RepoGraph) -> RepoGraph:
    file_nodes = [n for n in graph.nodes.values() if n.kind == "file"]

    # --- Pass 1: parse every file once; collect raw import names (Python)
    # so framework conventions can be detected before pass 2 runs ---
    parsed_cache: dict[str, tuple] = {}
    for file_node in file_nodes:
        path = Path(file_node.file_path)
        language = EXTENSION_LANGUAGE_MAP.get(path.suffix)
        family = LANGUAGE_FAMILY.get(path.suffix)
        if language is None or family is None:
            continue

        source_bytes = path.read_bytes()
        parser = Parser(language)
        tree = parser.parse(source_bytes)
        parsed_cache[file_node.id] = (tree.root_node, source_bytes, family)

        if family == "python":
            graph.raw_import_modules.update(_extract_python_imports(tree.root_node, source_bytes))
        # JS raw imports aren't fed into convention detection yet — no JS
        # convention plugins exist to consume them (see module docstring).

    conventions = detect_conventions(graph.raw_import_modules, graph)

    # --- Pass 2: add edges, per language family ---
    for file_node in file_nodes:
        if file_node.id not in parsed_cache:
            continue
        root, source_bytes, family = parsed_cache[file_node.id]
        path = Path(file_node.file_path)

        if family == "python":
            for module_name in _extract_python_imports(root, source_bytes):
                target_id = _module_name_to_file_id(module_name, graph)
                if target_id:
                    graph.edges.append(CodeEdge(source_id=file_node.id, target_id=target_id, relation="imports"))

            for convention in conventions:
                graph.edges.extend(convention.extract_dynamic_edges(root, source_bytes, file_node, graph))

            module_aliases, symbol_aliases = _extract_import_bindings(root, source_bytes)
            for call in _extract_call_sites(root, source_bytes):
                caller_id = f"{path}::{call['caller']}" if call["caller"] else file_node.id
                target_id = None
                if call["kind"] == "identifier":
                    same_file_id = f"{path}::{call['name']}"
                    if same_file_id in graph.nodes:
                        target_id = same_file_id
                    elif call["name"] in symbol_aliases:
                        module_name, original_name = symbol_aliases[call["name"]]
                        target_file = _module_name_to_file_id(module_name, graph)
                        if target_file:
                            candidate = f"{target_file}::{original_name}"
                            if candidate in graph.nodes:
                                target_id = candidate
                elif call["kind"] == "attribute" and call["object"] in module_aliases:
                    target_file = _module_name_to_file_id(module_aliases[call["object"]], graph)
                    if target_file:
                        candidate = f"{target_file}::{call['name']}"
                        if candidate in graph.nodes:
                            target_id = candidate
                if target_id:
                    graph.edges.append(CodeEdge(source_id=caller_id, target_id=target_id, relation="calls"))

        elif family == "javascript":
            for specifier in _extract_js_imports(root, source_bytes):
                target_id = _resolve_js_relative_import(path, specifier, graph)
                if target_id:
                    graph.edges.append(CodeEdge(source_id=file_node.id, target_id=target_id, relation="imports"))
            # TODO: function-level call resolution for JS/TS — needs an
            # export/import-aware resolver distinct from Python's.

    return graph