# backend/app/api/routes.py
# HTTP endpoints tying the frontend to the engine, the 5 modules,
# and the optional AI layer. Kept in one file for the scaffold —
# split into routers per module as the project grows.

from fastapi import APIRouter, UploadFile
from app.modules import health_index, pattern_detector, dead_code, impact_analyzer, similarity
from app.ai_layer.rag_chat import answer_question
from pydantic import BaseModel
from app.engine.parser import parse_repository
from app.engine.graph_builder import build_dependency_edges
from app.modules.health_index import compute_health_index
from app.modules.dead_code import find_dead_code

router = APIRouter()

class AnalyzeRequest(BaseModel):
    repo_path: str

@router.post("/repositories/upload")
async def upload_repository(file: UploadFile | None = None, github_url: str | None = None):
    """
    Accepts a ZIP upload or a GitHub URL, hands it to the Repository
    Intelligence Engine (parser.py + graph_builder.py), and returns a
    repository_id for subsequent module calls.
    TODO: save/clone into /tmp/repos, call parse_repository() + build_dependency_edges().
    """
    return {"repository_id": "placeholder"}

@router.post("/repositories/analyze")
def analyze_repository_path(payload: AnalyzeRequest):
    """
    Demo/dev endpoint: runs the full engine pipeline synchronously against
    a LOCAL filesystem path — not the real GitHub/ZIP upload flow yet (see
    the TODO in upload_repository above). Good enough for live demos and
    for wiring up the dashboard now; once real uploads exist, this should
    move into workers/tasks.py so a large repo doesn't block the request.
    """
    graph = build_dependency_edges(parse_repository(payload.repo_path))
    health = compute_health_index(graph)
    dead_code = find_dead_code(graph)

    return {
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "health_index": health,
        "dead_code": dead_code,
    }

@router.post("/repositories/graph")
def get_repository_graph(payload: AnalyzeRequest):
    """
    Returns just the FILE-level nodes and import/includes/calls edges
    between them, for visualization — not every function/class node,
    which would be far too dense to render clearly for a repo of any
    real size. Reuses the same engine pipeline as /analyze.
    """
    graph = build_dependency_edges(parse_repository(payload.repo_path))

    file_nodes = [
        {"id": n.id, "name": n.name}
        for n in graph.nodes.values() if n.kind == "file"
    ]
    file_ids = {n["id"] for n in file_nodes}
    file_edges = [
        {"source": e.source_id, "target": e.target_id, "relation": e.relation}
        for e in graph.edges
        if e.source_id in file_ids and e.target_id in file_ids
    ]

    return {"nodes": file_nodes, "edges": file_edges}


@router.get("/repositories/{repo_id}/health-index")
def get_health_index(repo_id: str):
    return health_index.compute_health_index(graph=None)  # TODO: load graph for repo_id


@router.get("/repositories/{repo_id}/patterns")
def get_patterns(repo_id: str):
    return pattern_detector.detect_patterns(graph=None)


@router.get("/repositories/{repo_id}/dead-code")
def get_dead_code(repo_id: str):
    return dead_code.find_dead_code(graph=None)


@router.post("/repositories/{repo_id}/impact")
def get_impact(repo_id: str, node_id: str):
    return impact_analyzer.analyze_impact(graph=None, changed_node_id=node_id)


@router.get("/repositories/similarity")
def get_similarity(repo_id_a: str, repo_id_b: str):
    return {"similarity": similarity.compute_similarity(graph_a=None, graph_b=None)}


@router.post("/repositories/{repo_id}/chat")
def chat(repo_id: str, question: str):
    """Optional AI layer — only meaningful if AI_LAYER_ENABLED=true."""
    return {"answer": answer_question(repo_id, question)}
