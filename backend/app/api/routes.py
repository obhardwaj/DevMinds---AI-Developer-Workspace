# backend/app/api/routes.py
# HTTP endpoints tying the frontend to the engine, the 5 modules,
# and the optional AI layer. Kept in one file for the scaffold —
# split into routers per module as the project grows.

from fastapi import APIRouter, UploadFile
from app.modules import health_index, pattern_detector, dead_code, impact_analyzer, similarity
from app.ai_layer.rag_chat import answer_question

router = APIRouter()


@router.post("/repositories/upload")
async def upload_repository(file: UploadFile | None = None, github_url: str | None = None):
    """
    Accepts a ZIP upload or a GitHub URL, hands it to the Repository
    Intelligence Engine (parser.py + graph_builder.py), and returns a
    repository_id for subsequent module calls.
    TODO: save/clone into /tmp/repos, call parse_repository() + build_dependency_edges().
    """
    return {"repository_id": "placeholder"}


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