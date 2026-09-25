# backend/app/engine/conventions/flask_convention.py
# Recognizes Flask's blueprint-registration convention:
#   from shop.routes import bp
#   app.register_blueprint(bp)
# This wires bp's module into the app via a VARIABLE reference, not a
# string literal like Django's include("app.urls") — a genuinely
# different wiring style, which is why this plugin needs its own
# (small, self-contained) import-binding lookup rather than reusing
# Django's string-based resolver.

from app.engine.graph_models import RepoGraph, CodeNode, CodeEdge


def _get_text(source_bytes: bytes, node) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8")


class FlaskConvention:
    name = "flask"

    def detect(self, raw_imports: set[str], graph: RepoGraph) -> bool:
        return any(m == "flask" or m.startswith("flask.") for m in raw_imports)

    def is_convention_file(self, node: CodeNode) -> bool:
        # Flask has no equivalent of Django's auto-loaded settings.py/admin.py —
        # everything is wired explicitly via imports or register_blueprint().
        # Nothing to special-case here; generic entry-point/__init__.py
        # handling in dead_code.py already covers Flask's app-factory pattern.
        return False

    def _symbol_import_sources(self, root, source_bytes: bytes) -> dict[str, str]:
        """Self-contained lookup: {local_name: module_name} for
        `from module import name` statements in this file. Deliberately
        separate from graph_builder.py's own import-binding logic — each
        convention plugin stays independent so adding/removing one never
        risks breaking another."""
        bindings: dict[str, str] = {}

        def walk(node):
            if node.type == "import_from_statement":
                module_node = node.child_by_field_name("module_name")
                module_name = _get_text(source_bytes, module_node) if module_node else ""
                for child in node.children:
                    if child.type == "dotted_name" and child != module_node:
                        bindings[_get_text(source_bytes, child)] = module_name
                    elif child.type == "aliased_import":
                        alias_node = child.child_by_field_name("alias")
                        if alias_node:
                            bindings[_get_text(source_bytes, alias_node)] = module_name
            for child in node.children:
                walk(child)

        walk(root)
        return bindings

    def extract_dynamic_edges(self, root, source_bytes: bytes, file_node: CodeNode, graph: RepoGraph) -> list[CodeEdge]:
        edges: list[CodeEdge] = []
        symbol_sources = self._symbol_import_sources(root, source_bytes)

        def walk(node):
            if node.type == "call":
                func_node = node.child_by_field_name("function")
                if (
                    func_node and func_node.type == "attribute"
                    and _get_text(source_bytes, func_node.child_by_field_name("attribute")) == "register_blueprint"
                ):
                    args_node = node.child_by_field_name("arguments")
                    if args_node and args_node.children:
                        first_arg = args_node.children[0]
                        if first_arg.type == "identifier":
                            arg_name = _get_text(source_bytes, first_arg)
                            module_name = symbol_sources.get(arg_name)
                            if module_name:
                                target_id = self._resolve_module(module_name, graph)
                                if target_id:
                                    edges.append(CodeEdge(
                                        source_id=file_node.id, target_id=target_id, relation="includes",
                                    ))
            for child in node.children:
                walk(child)

        walk(root)
        return edges

    def _resolve_module(self, dotted: str, graph: RepoGraph) -> str | None:
        target_suffix = dotted.replace(".", "/") + ".py"
        for node_id, node in graph.nodes.items():
            if node.kind == "file" and node.file_path.replace("\\", "/").endswith(target_suffix):
                return node_id
        return None