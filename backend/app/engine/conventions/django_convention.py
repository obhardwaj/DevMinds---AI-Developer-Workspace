# backend/app/engine/conventions/django_convention.py
# Recognizes Django's own file-loading and routing conventions that a
# plain import-graph can't see: settings.py/admin.py/apps.py are loaded
# by Django's app registry rather than imported, management commands are
# discovered by directory location, and include("app.urls") wires one
# urls.py into another via a string literal, not an import statement.

from app.engine.graph_models import RepoGraph, CodeNode, CodeEdge


def _get_text(source_bytes: bytes, node) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8")


def _string_literal_value(node, source_bytes: bytes) -> str | None:
    if node.type != "string":
        return None
    return _get_text(source_bytes, node).strip("'\"")


class DjangoConvention:
    name = "django"

    CONVENTION_FILENAMES = {"apps.py", "admin.py", "settings.py"}

    def detect(self, raw_imports: set[str], graph: RepoGraph) -> bool:
        return any(m == "django" or m.startswith("django.") for m in raw_imports)

    def is_convention_file(self, node: CodeNode) -> bool:
        if node.kind != "file":
            return False
        if node.name in self.CONVENTION_FILENAMES:
            return True
        normalized = node.file_path.replace("\\", "/")
        return "/management/commands/" in normalized

    def extract_dynamic_edges(self, root, source_bytes: bytes, file_node: CodeNode, graph: RepoGraph) -> list[CodeEdge]:
        edges: list[CodeEdge] = []

        def walk(node):
            if node.type == "call":
                func_node = node.child_by_field_name("function")
                if func_node and func_node.type == "identifier" and _get_text(source_bytes, func_node) == "include":
                    args_node = node.child_by_field_name("arguments")
                    if args_node:
                        for arg in args_node.children:
                            value = _string_literal_value(arg, source_bytes)
                            if value:
                                target_id = self._resolve_module(value, graph)
                                if target_id:
                                    edges.append(CodeEdge(source_id=file_node.id, target_id=target_id, relation="includes"))
                                break
            for child in node.children:
                walk(child)

        walk(root)
        return edges

    def _resolve_module(self, dotted: str, graph: RepoGraph) -> str | None:
        for suffix in (dotted, f"{dotted}.urls"):
            target_suffix = suffix.replace(".", "/") + ".py"
            for node_id, node in graph.nodes.items():
                if node.kind == "file" and node.file_path.replace("\\", "/").endswith(target_suffix):
                    return node_id
        return None