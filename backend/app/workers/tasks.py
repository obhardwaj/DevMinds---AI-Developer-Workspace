# backend/app/workers/tasks.py
# Celery tasks for anything too slow to run inline in a request —
# repository parsing, embedding generation, and module runs on large
# repos all happen here so the API stays responsive.

from celery import Celery
from app.config import settings

celery_app = Celery("adw_worker", broker=settings.REDIS_URL, backend=settings.REDIS_URL)


@celery_app.task
def analyze_repository_task(repo_id: str):
    """
    TODO: run parse_repository -> build_dependency_edges -> each of the
    5 modules -> (if AI_LAYER_ENABLED) embed_graph, storing results via
    app.db.models.AnalysisResult as each step completes.
    """
    pass