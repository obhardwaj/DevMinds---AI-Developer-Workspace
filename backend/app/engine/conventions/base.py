# backend/app/engine/conventions/base.py
# Interface every framework-convention plugin implements. A "convention"
# is a way a framework wires files/functions together WITHOUT a plain
# Python import — e.g. Django's include("app.urls") string, Flask's
# blueprint registration, a plugin registry, decorator-based routing.
# A rule-based (non-AI) engine can only recognize these if it's told
# about them explicitly, one framework at a time — this interface is
# how new frameworks (Flask, Express, Spring...) get added later
# without touching graph_builder.py or dead_code.py again.

from typing import Protocol
from app.engine.graph_models import RepoGraph, CodeNode, CodeEdge


class FrameworkConvention(Protocol):
    name: str

    def detect(self, raw_imports: set[str], graph: RepoGraph) -> bool:
        """True if this framework appears to be in use in this repo.
        `raw_imports` is every module name seen in any import statement,
        resolved or not (e.g. {"django.db", "shopapp.models", "os"})."""
        ...

    def is_convention_file(self, node: CodeNode) -> bool:
        """True if this file is wired in by the framework's own loading
        mechanism (not a plain import) and should never be flagged dead."""
        ...

    def extract_dynamic_edges(self, root, source_bytes: bytes, file_node: CodeNode, graph: RepoGraph) -> list[CodeEdge]:
        """Extra edges this file creates via framework-specific,
        non-import wiring (e.g. Django's include(...))."""
        ...