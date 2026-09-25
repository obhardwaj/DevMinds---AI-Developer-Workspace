# backend/app/engine/graph_builder.py
# Takes the nodes discovered by parser.py and adds dependency edges.
#
# Python: file->file "imports" edges, function->function "calls" edges
# (same-file and cross-file via resolved imports), plus framework
# "includes" edges from engine/conventions/ (Django, Flask so far).
#
# JavaScript/TypeScript: file->file "imports" edges (ESM + CommonJS
# require), AND function->function "calls" edges resolved through named
# imports, default imports, and namespace-object member calls. NOT
# resolved: method calls on a default-imported class instance (needs
# per-class method qualification — parser.py doesn't scope method node
# ids by class yet), re-exports (`export * from`), dynamic/computed
# require() calls, and `this.method()` (same limitation as Python's
# self.method() gap — both need type inference to do correctly).
#
# NOTE ON GRAMMAR NODE NAMES: the JS-side walkers below rely on specific
# tree-sitter-javascript node type names (e.g. "shorthand_property_identifier",
# "pair_pattern"). These occasionally shift between grammar versions — if a
# pattern isn't resolving, print node.type while walking to check the
# installed grammar's actual names before assuming the logic is wrong.

import os
from pathlib import Path
from tree_sitter import Parser
from app.engine.parser import EXTENSION_LANGUAGE_MAP, LANGUAGE_FAMILY
from app.engine.graph_models import RepoGraph, CodeEdge
from app.engine.conventions.registry import detect_conventions


def _get_text(source_bytes: bytes, node) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8")


# ============================================================
# Python: import + call extraction (unchanged from before)
# ============================================================

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


def _extract_python_call_sites(root, source_bytes: bytes) -> list[dict]:
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


# ============================================================
# JavaScript/TypeScript: import + export + call extraction (new)
# ============================================================

def _extract_js_imports(root, source_bytes: bytes) -> list[str]:
    """Returns raw import specifiers, e.g. ['./utils', 'express', '../models/user']."""
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
    """Resolves a relative specifier to a file node id, trying common
    extensions and index-file conventions. Bare package specifiers
    (no leading '.') are never resolved — they point outside the repo."""
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


def _extract_js_exports(root, source_bytes: bytes, file_path: Path) -> dict:
    """
    Returns {"named": {export_name: node_id}, "default": node_id_or_None}.
    Covers: export function/class/const, export default function/class/identifier,
    module.exports = { a, b }, module.exports = identifier,
    module.exports.foo = identifier, exports.foo = identifier.
    Re-exports and computed export targets are NOT covered.
    """
    named: dict[str, str] = {}
    default: str | None = None

    def node_id_for(name: str) -> str:
        return f"{file_path}::{name}"

    def walk(node):
        nonlocal default
        if node.type == "export_statement":
            is_default = any(child.type == "default" for child in node.children)
            declaration = node.child_by_field_name("declaration")
            if is_default:
                for child in node.children:
                    if child.type in ("function_declaration", "class_declaration"):
                        name_node = child.child_by_field_name("name")
                        if name_node:
                            default = node_id_for(_get_text(source_bytes, name_node))
                    elif child.type == "identifier":
                        default = node_id_for(_get_text(source_bytes, child))
            elif declaration is not None:
                if declaration.type in ("function_declaration", "class_declaration"):
                    name_node = declaration.child_by_field_name("name")
                    if name_node:
                        name = _get_text(source_bytes, name_node)
                        named[name] = node_id_for(name)
                elif declaration.type in ("lexical_declaration", "variable_declaration"):
                    for declarator in declaration.children:
                        if declarator.type == "variable_declarator":
                            name_node = declarator.child_by_field_name("name")
                            if name_node and name_node.type == "identifier":
                                name = _get_text(source_bytes, name_node)
                                named[name] = node_id_for(name)
        elif node.type == "assignment_expression":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if left is not None and right is not None:
                left_text = _get_text(source_bytes, left)
                if left_text == "module.exports":
                    if right.type == "object":
                        for prop in right.children:
                            if prop.type == "shorthand_property_identifier":
                                name = _get_text(source_bytes, prop)
                                named[name] = node_id_for(name)
                            elif prop.type == "pair":
                                key_node = prop.child_by_field_name("key")
                                value_node = prop.child_by_field_name("value")
                                if key_node and value_node and value_node.type == "identifier":
                                    key = _get_text(source_bytes, key_node).strip("'\"")
                                    named[key] = node_id_for(_get_text(source_bytes, value_node))
                    elif right.type == "identifier":
                        default = node_id_for(_get_text(source_bytes, right))
                elif left_text.startswith("module.exports.") or left_text.startswith("exports."):
                    export_name = left_text.split(".")[-1]
                    if right.type == "identifier":
                        named[export_name] = node_id_for(_get_text(source_bytes, right))
        for child in node.children:
            walk(child)

    walk(root)
    return {"named": named, "default": default}


def _extract_js_import_bindings(root, source_bytes: bytes) -> list[dict]:
    """
    Returns entries: {"specifier": str, "imported_name": "default"|"*"|<name>, "local_name": str}
    covering ESM imports and CommonJS require() forms.
    """
    bindings = []

    def walk(node):
        if node.type == "import_statement":
            source_node = node.child_by_field_name("source")
            specifier = _get_text(source_bytes, source_node).strip("'\"") if source_node else None
            if specifier is None:
                return
            import_clause = next((c for c in node.children if c.type == "import_clause"), None)
            if import_clause is not None:
                for clause_child in import_clause.children:
                    if clause_child.type == "identifier":
                        bindings.append({"specifier": specifier, "imported_name": "default",
                                          "local_name": _get_text(source_bytes, clause_child)})
                    elif clause_child.type == "namespace_import":
                        name_node = clause_child.children[-1] if clause_child.children else None
                        if name_node:
                            bindings.append({"specifier": specifier, "imported_name": "*",
                                              "local_name": _get_text(source_bytes, name_node)})
                    elif clause_child.type == "named_imports":
                        for spec in clause_child.children:
                            if spec.type == "import_specifier":
                                name_node = spec.child_by_field_name("name")
                                alias_node = spec.child_by_field_name("alias")
                                if name_node:
                                    original = _get_text(source_bytes, name_node)
                                    local = _get_text(source_bytes, alias_node) if alias_node else original
                                    bindings.append({"specifier": specifier, "imported_name": original,
                                                      "local_name": local})
        elif node.type == "variable_declarator":
            value_node = node.child_by_field_name("value")
            name_node = node.child_by_field_name("name")
            if value_node is not None and value_node.type == "call_expression":
                func_node = value_node.child_by_field_name("function")
                if func_node is not None and func_node.type == "identifier" and _get_text(source_bytes, func_node) == "require":
                    args_node = value_node.child_by_field_name("arguments")
                    specifier = None
                    for arg in (args_node.children if args_node else []):
                        if arg.type == "string":
                            specifier = _get_text(source_bytes, arg).strip("'\"")
                            break
                    if specifier is not None and name_node is not None:
                        if name_node.type == "identifier":
                            bindings.append({"specifier": specifier, "imported_name": "*",
                                              "local_name": _get_text(source_bytes, name_node)})
                        elif name_node.type == "object_pattern":
                            for prop in name_node.children:
                                if prop.type == "shorthand_property_identifier_pattern":
                                    name = _get_text(source_bytes, prop)
                                    bindings.append({"specifier": specifier, "imported_name": name, "local_name": name})
                                elif prop.type == "pair_pattern":
                                    key_node = prop.child_by_field_name("key")
                                    value_node2 = prop.child_by_field_name("value")
                                    if key_node and value_node2:
                                        bindings.append({"specifier": specifier,
                                                          "imported_name": _get_text(source_bytes, key_node),
                                                          "local_name": _get_text(source_bytes, value_node2)})
        for child in node.children:
            walk(child)

    walk(root)
    return bindings


def _extract_js_call_sites(root, source_bytes: bytes) -> list[dict]:
    """
    Returns one entry per call_expression:
      {"caller": <enclosing function/method name, "" if module-level>,
       "kind": "identifier" | "member" | "other", "name": ..., "object": ...}
    "other" covers this.method(), chained calls, computed member access —
    left unresolved (see module docstring).
    """
    calls = []

    def enclosing_name(node) -> str | None:
        if node.type in ("function_declaration", "method_definition"):
            name_node = node.child_by_field_name("name")
            return _get_text(source_bytes, name_node) if name_node else None
        if node.type == "variable_declarator":
            value_node = node.child_by_field_name("value")
            name_node = node.child_by_field_name("name")
            if value_node is not None and value_node.type in ("arrow_function", "function_expression") and name_node is not None:
                return _get_text(source_bytes, name_node)
        return None

    def walk(node, current_function: str):
        name = enclosing_name(node)
        if name is not None:
            current_function = name

        if node.type == "call_expression":
            func_node = node.child_by_field_name("function")
            if func_node is not None:
                if func_node.type == "identifier":
                    calls.append({"caller": current_function, "kind": "identifier",
                                  "name": _get_text(source_bytes, func_node), "object": None})
                elif func_node.type == "member_expression":
                    obj_node = func_node.child_by_field_name("object")
                    prop_node = func_node.child_by_field_name("property")
                    if obj_node is not None and prop_node is not None and obj_node.type == "identifier":
                        calls.append({"caller": current_function, "kind": "member",
                                      "name": _get_text(source_bytes, prop_node),
                                      "object": _get_text(source_bytes, obj_node)})
                    else:
                        calls.append({"caller": current_function, "kind": "other", "name": None, "object": None})
                else:
                    calls.append({"caller": current_function, "kind": "other", "name": None, "object": None})

        for child in node.children:
            walk(child, current_function)

    walk(root, current_function="")
    return calls


# ============================================================
# Main entry point
# ============================================================

def build_dependency_edges(graph: RepoGraph) -> RepoGraph:
    file_nodes = [n for n in graph.nodes.values() if n.kind == "file"]

    # --- Pass 1: parse every file once; collect Python raw imports (for
    # framework-convention detection) and JS export tables (needed before
    # any file's imports/calls can be resolved against them) ---
    parsed_cache: dict[str, tuple] = {}
    file_js_exports: dict[str, dict] = {}
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
        elif family == "javascript":
            file_js_exports[file_node.id] = _extract_js_exports(tree.root_node, source_bytes, path)

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
            for call in _extract_python_call_sites(root, source_bytes):
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

            import_bindings = _extract_js_import_bindings(root, source_bytes)
            bindings_by_local_name = {b["local_name"]: b for b in import_bindings}

            for call in _extract_js_call_sites(root, source_bytes):
                caller_id = f"{path}::{call['caller']}" if call["caller"] else file_node.id
                target_id = None

                if call["kind"] == "identifier":
                    same_file_id = f"{path}::{call['name']}"
                    if same_file_id in graph.nodes:
                        target_id = same_file_id
                    elif call["name"] in bindings_by_local_name:
                        binding = bindings_by_local_name[call["name"]]
                        target_file = _resolve_js_relative_import(path, binding["specifier"], graph)
                        if target_file:
                            target_exports = file_js_exports.get(target_file, {"named": {}, "default": None})
                            if binding["imported_name"] == "default":
                                target_id = target_exports["default"]
                            elif binding["imported_name"] != "*":
                                target_id = target_exports["named"].get(binding["imported_name"])

                elif call["kind"] == "member" and call["object"] in bindings_by_local_name:
                    binding = bindings_by_local_name[call["object"]]
                    if binding["imported_name"] == "*":
                        target_file = _resolve_js_relative_import(path, binding["specifier"], graph)
                        if target_file:
                            target_exports = file_js_exports.get(target_file, {"named": {}, "default": None})
                            target_id = target_exports["named"].get(call["name"])
                    # Foo.method() on a default-imported class instance: not
                    # resolved — see module docstring.

                if target_id and target_id in graph.nodes:
                    graph.edges.append(CodeEdge(source_id=caller_id, target_id=target_id, relation="calls"))

    return graph