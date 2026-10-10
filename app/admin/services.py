from app.extensions import db
from app.models import (
    Game,
    GameConfirmation,
    PlayerGame,
    Team,
)


ALLOWED_ROLES = ("USER", "MODERATOR")


def set_role(player, role):
    if role not in ALLOWED_ROLES:
        return False

    if player.role == "ADMIN":
        return False

    player.role = role

    return True


def block_player(player):
    if player.role == "ADMIN":
        return False

    player.is_blocked = True

    return True


def unblock_player(player):
    player.is_blocked = False

    return True


def delete_player(player):
    if player.role == "ADMIN":
        return False

    if player.is_deleted:
        return False

    player.is_deleted = True

    cancel_player_pending_games(player)

    return True


def restore_player(player):
    if not player.is_deleted:
        return False

    player.is_deleted = False

    return True


def cancel_player_pending_games(player):
    pending_game_ids = load_pending_game_ids_for_player(player)

    if not pending_game_ids:
        return

    for game_id in pending_game_ids:
        game = db.session.get(Game, game_id)

        if game is None:
            continue

        game.status = "MODERATION"

    confirmations = (
        GameConfirmation.query
        .filter(
            GameConfirmation.game_id.in_(pending_game_ids),
            GameConfirmation.player_id == player.id,
            GameConfirmation.response == "WAIT",
        )
        .all()
    )

    for confirmation in confirmations:
        confirmation.response = "CONFLICT"


def load_pending_game_ids_for_player(player):
    rows = (
        db.session.query(Game.id)
        .join(Team, Team.game_id == Game.id)
        .join(PlayerGame, PlayerGame.team_id == Team.id)
        .filter(
            PlayerGame.player_id == player.id,
            Game.status == "PENDING",
        )
        .distinct()
        .all()
    )

    return [row[0] for row in rows]