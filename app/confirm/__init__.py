from flask import Blueprint

confirm_bp = Blueprint(
    "confirm",
    __name__,
    url_prefix="/confirm",
)

from app.confirm import routes