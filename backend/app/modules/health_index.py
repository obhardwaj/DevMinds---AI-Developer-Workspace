# backend/app/modules/health_index.py
# Repository Health Index: combines complexity, documentation, test
# coverage, security, and duplication signals into one 0-100 score.
# Reads only from the RepoGraph (plus source files, for security and
# duplication, which need actual code text) — no AI involved.

import hashlib
from pathlib import Path
from app.engine.graph_models import RepoGraph

WEIGHTS = {
    "complexity": 0.25,
    "documentation": 0.20,
    "test_coverage": 0.20,
    "security": 0.20,
    "duplication": 0.15,
}

LONG_FUNCTION_THRESHOLD = 40   # lines; functions longer than this count as "complex"
MIN_DUPLICATE_LINES = 4        # ignore trivial 1-2 line functions when checking duplication

RISKY_PATTERNS = ["eval(", "exec(", "os.system(", "subprocess.call(", "pickle.loads("]


def _score_complexity(graph: RepoGraph) -> float:
    functions = [n for n in graph.nodes.values() if n.kind == "function"]
    if not functions:
        return 100.0
    long_ones = sum(1 for f in functions if (f.end_line - f.start_line) > LONG_FUNCTION_THRESHOLD)
    return round(100 * (1 - long_ones / len(functions)), 1)


def _score_documentation(graph: RepoGraph) -> float:
    documentable = [n for n in graph.nodes.values() if n.kind in ("function", "class")]
    if not documentable:
        return 100.0
    documented = sum(1 for n in documentable if n.has_docstring)
    return round(100 * documented / len(documentable), 1)


def _score_test_coverage(graph: RepoGraph) -> float:
    files = [n for n in graph.nodes.values() if n.kind == "file"]
    if not files:
        return 0.0
    test_files = sum(1 for f in files if "test" in f.name.lower())
    ratio = test_files / max(len(files) - test_files, 1)
    return round(min(100, ratio / (1 / 3) * 100), 1)


def _read_file_cached(path: str, cache: dict[str, list[str]]) -> list[str]:
    """Reads a file's lines once and reuses them for both security and
    duplication scoring, instead of each scorer opening every file itself."""
    if path not in cache:
        try:
            cache[path] = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            cache[path] = []
    return cache[path]


def _score_security(graph: RepoGraph, file_cache: dict[str, list[str]]) -> tuple[float, list[str]]:
    """
    Flags files containing risky calls (eval, exec, shell execution, unsafe
    deserialization). This is a pattern-match scan, not real taint analysis —
    it will miss disguised usage and may flag safe uses inside comments/strings.
    Good enough for a first pass; a real static-analysis pass is future work.
    """
    files = [n for n in graph.nodes.values() if n.kind == "file"]
    if not files:
        return 100.0, []

    flagged: list[str] = []
    for f in files:
        lines = _read_file_cached(f.file_path, file_cache)
        content = "\n".join(lines)
        if any(pattern in content for pattern in RISKY_PATTERNS):
            flagged.append(f.file_path)

    score = round(100 * (1 - len(flagged) / len(files)), 1)
    return score, flagged


def _score_duplication(graph: RepoGraph, file_cache: dict[str, list[str]]) -> tuple[float, list[list[str]]]:
    """
    Exact-match duplication: normalizes each function's body (strips blank
    lines and leading/trailing whitespace per line) and groups functions
    whose normalized text is identical. This only catches copy-pasted code,
    not renamed-variable or reordered duplicates — a fuzzier comparison
    (e.g. token-sequence similarity) is future work, in the spirit of the
    similarity module's own approach.
    """
    functions = [
        n for n in graph.nodes.values()
        if n.kind == "function" and (n.end_line - n.start_line) >= MIN_DUPLICATE_LINES
    ]
    if not functions:
        return 100.0, []

    groups: dict[str, list[str]] = {}
    for fn in functions:
        lines = _read_file_cached(fn.file_path, file_cache)
        body_lines = [line.strip() for line in lines[fn.start_line - 1:fn.end_line] if line.strip()]
        normalized = "\n".join(body_lines)
        digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()
        groups.setdefault(digest, []).append(fn.id)

    duplicate_groups = [ids for ids in groups.values() if len(ids) > 1]
    duplicated_count = sum(len(ids) for ids in duplicate_groups)
    score = round(100 * (1 - duplicated_count / len(functions)), 1)
    return score, duplicate_groups


def compute_health_index(graph: RepoGraph) -> dict:
    file_cache: dict[str, list[str]] = {}

    security_score, flagged_files = _score_security(graph, file_cache)
    duplication_score, duplicate_groups = _score_duplication(graph, file_cache)

    breakdown = {
        "complexity": _score_complexity(graph),
        "documentation": _score_documentation(graph),
        "test_coverage": _score_test_coverage(graph),
        "security": security_score,
        "duplication": duplication_score,
    }
    score = sum(breakdown[k] * w for k, w in WEIGHTS.items())

    return {
        "score": round(score, 1),
        "breakdown": breakdown,
        "details": {
            "flagged_files": flagged_files,          # files with risky calls
            "duplicate_groups": duplicate_groups,     # groups of function ids with identical bodies
        },
    }