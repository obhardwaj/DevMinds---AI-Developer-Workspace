# backend/test_flask_convention.py
# Throwaway check — confirms the Flask convention plugin correctly
# detects register_blueprint() wiring. Not meant to be committed long-term.

import textwrap
from pathlib import Path

Path("test_flask_app").mkdir(exist_ok=True)
Path("test_flask_app/routes.py").write_text(textwrap.dedent("""
    from flask import Blueprint
    bp = Blueprint("shop", __name__)

    @bp.route("/products")
    def list_products():
        return "ok"
"""))
Path("test_flask_app/app.py").write_text(textwrap.dedent("""
    from flask import Flask
    from routes import bp

    app = Flask(__name__)
    app.register_blueprint(bp)
"""))

from app.engine.parser import parse_repository
from app.engine.graph_builder import build_dependency_edges
from app.modules.dead_code import find_dead_code

graph = build_dependency_edges(parse_repository("test_flask_app"))
result = find_dead_code(graph)
print("Detected frameworks:", result["detected_frameworks"])
print("Orphaned files:", result["orphaned_files"])