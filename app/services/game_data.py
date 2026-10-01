from app.extensions import db
from app.models import (
    Faction,
    FactionListFaction,
    Game,
    GameConfirmation,
    GameFaction,
    GameVersion,
    PlayerGame,
    Review,
    Team, Player,
)


def load_versions(conflict):
    rows = (
        GameVersion.query
        .filter(GameVersion.game_conflict_id == conflict.id)
        .all()
    )

    games_by_id = {
        row.game.id: row.game
        for row in rows
        if row.game is not None
    }

    games = list(games_by_id.values())

    games.sort(
        key=lambda game: (
            0 if game.id == conflict.original_game_id else 1,
            game.created_at,
        )
    )

    versions = []

    for index, game in enumerate(games):
        versions.append({
            "game": game,
            "author": game.creator,
            "is_original": game.id == conflict.original_game_id,
            "page_index": index + 1,
            "response": None,
        })

    return versions


def load_version_data(game):
    teams = (
        Team.query
        .filter(Team.game_id == game.id)
        .order_by(Team.command_number)
        .all()
    )

    team_ids = [team.id for team in teams]

    players_by_team = {}

    if team_ids:
        player_games = (
            PlayerGame.query
            .filter(PlayerGame.team_id.in_(team_ids))
            .all()
        )

        for player_game in player_games:
            players_by_team.setdefault(
                player_game.team_id,
                [],
            ).append(player_game)

    factions_by_player_game = {}

    player_game_ids = [
        pg.id
        for list_ in players_by_team.values()
        for pg in list_
    ]

    if player_game_ids:
        game_factions = (
            GameFaction.query
            .filter(GameFaction.player_game_id.in_(player_game_ids))
            .all()
        )

        for game_faction in game_factions:
            factions_by_player_game.setdefault(
                game_faction.player_game_id,
                [],
            ).append(game_faction.faction)

    teams_data = []

    for team in teams:
        players_data = []

        for player_game in players_by_team.get(team.id, []):
            players_data.append({
                "player": player_game.player,
                "factions": factions_by_player_game.get(
                    player_game.id, []
                ),
            })

        teams_data.append({
            "team": team,
            "players": players_data,
        })

    return {
        "game": game,
        "teams": teams_data,
    }


def load_own_confirmations(game_ids, user):
    if not game_ids:
        return {}

    confirmations = (
        GameConfirmation.query
        .filter(
            GameConfirmation.game_id.in_(game_ids),
            GameConfirmation.player_id == user.id,
        )
        .all()
    )

    return {
        confirmation.game_id: confirmation
        for confirmation in confirmations
    }


def load_own_reviews(conflict, user):
    reviews = (
        Review.query
        .filter(
            Review.game_id == conflict.original_game_id,
            Review.author == user.id,
        )
        .all()
    )

    return reviews


def load_review_targets(conflict, user):
    own_version = (
        db.session.query(Game)
        .join(GameVersion, GameVersion.game_id == Game.id)
        .filter(
            GameVersion.game_conflict_id == conflict.id,
            Game.created_by == user.id,
        )
        .first()
    )

    if own_version is not None:
        source_game_id = own_version.id
    else:
        source_game_id = conflict.original_game_id

    if source_game_id is None:
        return []

    teams = (
        Team.query
        .filter(Team.game_id == source_game_id)
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

    participant_ids = {
        player_game.player_id
        for player_game in player_games
    }

    participant_ids.discard(user.id)

    if not participant_ids:
        return []

    players = (
        Player.query
        .filter(Player.id.in_(participant_ids))
        .order_by(Player.nickname)
        .all()
    )

    existing_reviews = (
        Review.query
        .filter(
            Review.game_id == conflict.original_game_id,
            Review.author == user.id,
            Review.player_id.in_(participant_ids),
        )
        .all()
    )

    reviews_by_player_id = {
        review.player_id: review
        for review in existing_reviews
    }

    targets = []

    for player in players:
        targets.append({
            "player": player,
            "review": reviews_by_player_id.get(player.id),
        })

    return targets


def load_faction_list_members(faction_list_ids):
    if not faction_list_ids:
        return {}

    items = (
        db.session.query(
            FactionListFaction.faction_list_id,
            Faction,
        )
        .join(Faction, Faction.id == FactionListFaction.faction_id)
        .filter(
            FactionListFaction.faction_list_id.in_(faction_list_ids)
        )
        .all()
    )

    result = {}

    for faction_list_id, faction in items:
        result.setdefault(faction_list_id, []).append(faction)

    return result


def load_game_reviews(game):
    return (
        Review.query
        .filter(Review.game_id == game.id)
        .order_by(Review.created_at.desc())
        .all()
    )