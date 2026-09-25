# backend/app/modules/dead_code.py
# Dead Code Detection: flags (1) files nothing imports/includes and that
# aren't a generic entry point, test file, or a file a detected framework
# convention (see engine/conventions/) recognizes as its own, and (2)
# private functions/methods never called within their own file.
#
# LIMITATION 1: cross-file calls through self.method() or an object
# instance aren't resolved (needs type inference) — public functions
# aren't checked for dead-code status yet.
# LIMITATION 2: orphaned-file detection is only as good as the framework
# conventions currently implemented (Django, so far — see
# engine/conventions/registry.py). A repo using an unrecognized
# framework's dynamic wiring may still show false-positive orphaned files.

import re
from app.engine.graph_models import RepoGraph
from app.engine.conventions.registry import detect_conventions

ENTRY_FILENAMES = {"manage.py", "main.py", "app.py", "wsgi.py", "asgi.py", "server.py", "index.py"}
TEST_FILENAME_PATTERN = re.compile(r"^(tests?|test_.*|.*_test)\.py$")


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def _is_generic_non_dead_file(node) -> bool:
    """Truly framework-agnostic exclusions: known entry points, __init__.py
    package markers, and test files — true for any Python project."""
    return node.name in ENTRY_FILENAMES or node.name == "__init__.py" or bool(TEST_FILENAME_PATTERN.match(node.name))


def find_entry_points(graph: RepoGraph) -> set[str]:
    conventions = detect_conventions(graph.raw_import_modules, graph)
    entry_points = set()
    for node in graph.nodes.values():
        if node.kind != "file":
            continue
        if _is_generic_non_dead_file(node):
            entry_points.add(node.id)
        elif any(c.is_convention_file(node) for c in conventions):
            entry_points.add(node.id)
    return entry_points


def _find_orphaned_files(graph: RepoGraph, entry_points: set[str]) -> list[str]:
    all_files = {n.id for n in graph.nodes.values() if n.kind == "file"}
    used_files = {e.target_id for e in graph.edges if e.relation in ("imports", "includes")}
    return sorted(all_files - used_files - entry_points)


def _find_dead_private_functions(graph: RepoGraph) -> list[str]:
    private_functions = [
        n for n in graph.nodes.values()
        if n.kind == "function" and n.name.startswith("_") and not _is_dunder(n.name)
    ]
    called_targets = {e.target_id for e in graph.edges if e.relation == "calls"}
    return sorted(f.id for f in private_functions if f.id not in called_targets)


def find_dead_code(graph: RepoGraph, entry_points: set[str] | None = None) -> dict:
    if entry_points is None:
        entry_points = find_entry_points(graph)

    detected = [c.name for c in detect_conventions(graph.raw_import_modules, graph)]

    return {
        "orphaned_files": _find_orphaned_files(graph, entry_points),
        "dead_private_functions": _find_dead_private_functions(graph),
        "detected_frameworks": detected,
        "note": (
            "Public functions aren't checked yet — resolving self.method()/instance "
            "calls needs type inference. Orphaned-file accuracy depends on which "
            "framework conventions are implemented (currently: Django only) — an "
            "unrecognized framework's dynamic wiring may still cause false positives."
        ),
    }