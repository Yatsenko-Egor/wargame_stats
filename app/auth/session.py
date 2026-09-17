import logging

from flask import session

logger = logging.getLogger(__name__)


def login_user(player_id: int) -> None:
    session["player_id"] = player_id


def logout_user() -> None:
    session.pop("player_id", None)


def get_current_user_id():
    return session.get("player_id")


def get_current_user():
    player_id = get_current_user_id()

    if player_id is None:
        return None

    from app import db
    from app.models.player import Player

    try:
        return db.session.get(Player, player_id)
    except Exception:
        logger.exception("Failed to load current user")
        return None