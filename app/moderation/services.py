from datetime import datetime, timedelta, timezone

from flask import current_app

from app.extensions import db
from app.models import (
    Game,
    GameFaction,
    PlayerFactionStatistics,
    PlayerGame,
    Review,
    Team,
)
from app.services.game_creation import find_or_create_faction_list
from app.services.game_data import load_versions
from app.services.game_finalize import (
    finalize_game,
)


CLEARED_REVIEW_TEXT = "[удалено модератором]"


def finalize_by_moderator(conflict, game):
    return finalize_game(conflict, game)


def cancel_conflict(conflict):
    versions = load_versions(conflict)
    version_ids = [version["game"].id for version in versions]

    if version_ids:
        (
            Review.query
            .filter(Review.game_id.in_(version_ids))
            .delete(synchronize_session=False)
        )

    db.session.delete(conflict)
    db.session.flush()

    for version in versions:
        game = db.session.get(Game, version["game"].id)

        if game is not None:
            db.session.delete(game)


def cancel_official_game(game):
    decrease_statistics_for_game(game)

    game.status = "CANCELLED"


def restore_official_game(game):
    increase_statistics_for_game(game)

    game.status = "OFFICIAL"


def clear_review_text(review):
    review.text = CLEARED_REVIEW_TEXT


def decrease_statistics_for_game(game):
    statistics_items = collect_statistics_items(game)

    for item in statistics_items:
        statistics = (
            PlayerFactionStatistics.query
            .filter(
                PlayerFactionStatistics.faction_list_id
                == item["faction_list_id"],
                PlayerFactionStatistics.player_id
                == item["player_id"],
                PlayerFactionStatistics.edition_id
                == game.edition_id,
            )
            .first()
        )

        if statistics is None:
            continue

        statistics.game_count = max(0, statistics.game_count - 1)

        if item["result"] == "WIN":
            statistics.wins = max(0, statistics.wins - 1)
        elif item["result"] == "LOSS":
            statistics.losses = max(0, statistics.losses - 1)


def increase_statistics_for_game(game):
    statistics_items = collect_statistics_items(game)

    for item in statistics_items:
        statistics = (
            PlayerFactionStatistics.query
            .filter(
                PlayerFactionStatistics.faction_list_id
                == item["faction_list_id"],
                PlayerFactionStatistics.player_id
                == item["player_id"],
                PlayerFactionStatistics.edition_id
                == game.edition_id,
            )
            .first()
        )

        if statistics is None:
            statistics = PlayerFactionStatistics(
                faction_list_id=item["faction_list_id"],
                player_id=item["player_id"],
                edition_id=game.edition_id,
                game_count=0,
                wins=0,
                losses=0,
            )
            db.session.add(statistics)

        statistics.game_count += 1

        if item["result"] == "WIN":
            statistics.wins += 1
        elif item["result"] == "LOSS":
            statistics.losses += 1


def collect_statistics_items(game):
    teams = (
        Team.query
        .filter(Team.game_id == game.id)
        .order_by(Team.command_number)
        .all()
    )

    team_ids = [team.id for team in teams]

    if not team_ids:
        return []

    player_games = (
        PlayerGame.query
        .filter(PlayerGame.team_id.in_(team_ids))
        .all()
    )

    processed_players = set()
    items = []

    for team in teams:
        team_player_games = [
            player_game
            for player_game in player_games
            if player_game.team_id == team.id
        ]

        for player_game in team_player_games:
            player_id = player_game.player_id

            if player_id in processed_players:
                continue

            processed_players.add(player_id)

            faction_ids = [
                row[0]
                for row in (
                    db.session.query(GameFaction.faction_id)
                    .filter(GameFaction.player_game_id == player_game.id)
                    .all()
                )
            ]

            if not faction_ids:
                continue

            faction_list_id = find_or_create_faction_list(faction_ids)

            items.append({
                "player_id": player_id,
                "faction_list_id": faction_list_id,
                "result": team.result,
            })

    return items


def acquire_lock(conflict, user):
    if conflict.status != "OPEN":
        return False

    if conflict.viewed_by is None:
        conflict.viewed_by = user.id
        conflict.viewed_at = datetime.now(timezone.utc)
        return True

    if conflict.viewed_by == user.id:
        conflict.viewed_at = datetime.now(timezone.utc)
        return True

    if is_lock_expired(conflict):
        conflict.viewed_by = user.id
        conflict.viewed_at = datetime.now(timezone.utc)
        return True

    return False


def release_lock(conflict, user):
    if conflict.viewed_by != user.id:
        return False

    conflict.viewed_by = None
    conflict.viewed_at = None

    return True


def update_lock_heartbeat(conflict, user):
    if conflict.viewed_by != user.id:
        return False

    conflict.viewed_at = datetime.now(timezone.utc)

    return True


def is_locked_by_other(conflict, user):
    if conflict.viewed_by is None:
        return False

    if conflict.viewed_by == user.id:
        return False

    if is_lock_expired(conflict):
        return False

    return True


def is_lock_expired(conflict):
    if conflict.viewed_at is None:
        return True

    timeout = current_app.config["MODERATION_LOCK_TIMEOUT"]

    threshold = datetime.now(timezone.utc) - timedelta(
        seconds=timeout
    )

    return conflict.viewed_at < threshold