from app.extensions import db
from app.models import (
    Game,
    GameConfirmation,
    GameFaction,
    PlayerFactionStatistics,
    PlayerGame,
    Review,
    Team,
)
from app.services.game_creation import find_or_create_faction_list
from app.services.game_data import load_versions


def try_finalize(conflict):
    versions = load_versions(conflict)

    for version in versions:
        game = version["game"]

        if _is_fully_confirmed(game):
            return finalize_game(conflict, game)

    return None


def _is_fully_confirmed(game):
    teams = (
        Team.query
        .filter(Team.game_id == game.id)
        .all()
    )

    team_ids = [team.id for team in teams]

    if not team_ids:
        return False

    participant_ids = {
        row[0]
        for row in (
            db.session.query(PlayerGame.player_id)
            .filter(PlayerGame.team_id.in_(team_ids))
            .distinct()
            .all()
        )
    }

    if not participant_ids:
        return False

    confirmations = (
        GameConfirmation.query
        .filter(GameConfirmation.game_id == game.id)
        .all()
    )

    if len(confirmations) != len(participant_ids):
        return False

    return all(
        confirmation.response == "CONFIRM"
        for confirmation in confirmations
    )


def finalize_game(conflict, game):
    update_statistics_for_game(game)

    original_game_id = conflict.original_game_id

    if original_game_id is not None and original_game_id != game.id:
        (
            Review.query
            .filter(Review.game_id == original_game_id)
            .update(
                {"game_id": game.id},
                synchronize_session=False,
            )
        )

    game.status = "OFFICIAL"

    official_game_id = game.id

    other_game_ids = [
        version["game"].id
        for version in load_versions(conflict)
        if version["game"].id != official_game_id
    ]

    db.session.delete(conflict)
    db.session.flush()

    for other_id in other_game_ids:
        other_game = db.session.get(Game, other_id)

        if other_game is not None:
            db.session.delete(other_game)

    return official_game_id


def update_statistics_for_game(game):
    teams = (
        Team.query
        .filter(Team.game_id == game.id)
        .order_by(Team.command_number)
        .all()
    )

    team_ids = [team.id for team in teams]

    if not team_ids:
        return

    player_games = (
        PlayerGame.query
        .filter(PlayerGame.team_id.in_(team_ids))
        .all()
    )

    processed_players = set()

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

            statistics = (
                PlayerFactionStatistics.query
                .filter(
                    PlayerFactionStatistics.faction_list_id
                    == faction_list_id,
                    PlayerFactionStatistics.player_id == player_id,
                    PlayerFactionStatistics.edition_id == game.edition_id,
                )
                .first()
            )

            if statistics is None:
                statistics = PlayerFactionStatistics(
                    faction_list_id=faction_list_id,
                    player_id=player_id,
                    edition_id=game.edition_id,
                    game_count=0,
                    wins=0,
                    losses=0,
                )
                db.session.add(statistics)

            statistics.game_count += 1

            if team.result == "WIN":
                statistics.wins += 1
            elif team.result == "LOSS":
                statistics.losses += 1