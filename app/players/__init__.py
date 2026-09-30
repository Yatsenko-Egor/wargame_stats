from flask import Blueprint

players_bp = Blueprint(
    "players",
    __name__,
    url_prefix="/players",
)

from app.players import routes