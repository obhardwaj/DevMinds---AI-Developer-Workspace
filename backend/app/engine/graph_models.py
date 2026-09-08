# backend/app/engine/graph_models.py
# Plain data structures for the Repository Intelligence Engine's graph
# model. Every module (health index, pattern detector, etc.) reads from
# a RepoGraph instance rather than re-parsing source files itself.

from dataclasses import dataclass, field


@dataclass
class CodeNode:
    """A single file, class, or function in the repository graph."""
    id: str                 # e.g. "src/utils/parser.py::parse_file"
    kind: str                # "file" | "class" | "function"
    file_path: str
    name: str
    start_line: int
    end_line: int


@dataclass
class CodeEdge:
    """A relationship between two nodes: import, call, or inheritance."""
    source_id: str
    target_id: str
    relation: str            # "imports" | "calls" | "inherits"


@dataclass
class RepoGraph:
    """The full structured model of one repository. This is the
    single source of truth every module (Health Index, Pattern
    Detector, Dead Code Detection, Impact Analyzer, Similarity)
    queries — none of them re-parse the codebase themselves."""
    nodes: dict[str, CodeNode] = field(default_factory=dict)
    edges: list[CodeEdge] = field(default_factory=list)