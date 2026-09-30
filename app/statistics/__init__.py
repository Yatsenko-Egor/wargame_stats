from flask import Blueprint

statistics_bp = Blueprint(
    "statistics",
    __name__,
    url_prefix="/statistics",
)

from app.statistics import wargames
from app.statistics import factions
