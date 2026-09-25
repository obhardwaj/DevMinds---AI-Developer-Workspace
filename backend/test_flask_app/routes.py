
from flask import Blueprint
bp = Blueprint("shop", __name__)

@bp.route("/products")
def list_products():
    return "ok"
