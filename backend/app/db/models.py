# backend/app/db/models.py
# ORM tables: one row per analyzed repository, plus a row per module
# run against it (health score, similarity result, etc.).

from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    source_url = Column(String, nullable=True)   # GitHub URL, if applicable
    name = Column(String)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class AnalysisResult(Base):
    """Generic result row — one per module run (health_index, dead_code, etc.)."""
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"))
    module_name = Column(String)          # e.g. "health_index", "dead_code"
    score = Column(Float, nullable=True)  # used by Health Index / Similarity
    data = Column(JSON)                   # module-specific structured output
    created_at = Column(DateTime(timezone=True), server_default=func.now())
