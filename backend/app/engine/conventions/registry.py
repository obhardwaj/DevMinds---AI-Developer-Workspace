# backend/app/engine/conventions/registry.py
# Every known framework-convention plugin, and the logic to figure out
# which ones apply to the repo currently being analyzed. To support a
# new framework later, write a new file implementing FrameworkConvention
# (see base.py) and add one line to ALL_CONVENTIONS below — nothing else
# in the engine needs to change.

from app.engine.conventions.django_convention import DjangoConvention
from app.engine.conventions.flask_convention import FlaskConvention

ALL_CONVENTIONS = [DjangoConvention(), FlaskConvention()]


def detect_conventions(raw_imports: set[str], graph) -> list:
    return [c for c in ALL_CONVENTIONS if c.detect(raw_imports, graph)]