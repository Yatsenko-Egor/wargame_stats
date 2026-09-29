from flask import abort, g, render_template, request
from sqlalchemy import func

from app.extensions import db
from app.models import (
    Player,
    Review,
    Game,
    PlayerFaction,
    PlayerFactionStatistics,
    FactionListFaction,
    Faction,
    Wargame,
    WargameEdition,
    Team,
    PlayerGame,
    GameConfirmation, GameVersion,
)
from app.profile import profile_bp

REVIEWS_PER_PAGE = 10
GAMES_PER_PAGE = 10


@profile_bp.route("/<nickname>")
def view(nickname):
    player = load_player(nickname)

    is_self = (
            g.current_user is not None
            and g.current_user.id == player.id
    )

    rating, rating_count = load_rating(player)

    player_factions = load_player_factions(player)

    player_faction_ids = {
        player_faction.faction_id
        for player_faction in player_factions
    }

    available_wargame_ids = {
        player_faction.faction.wargame_id
        for player_faction in player_factions
    }

    (
        wargames,
        editions,
        editions_by_wargame,
        editions_by_id,
        wargames_by_id,
    ) = load_wargames_and_editions(available_wargame_ids)

    selected_wargame_id = resolve_selected_wargame(request, wargames_by_id)

    available_editions = (
        editions_by_wargame.get(selected_wargame_id, [])
        if selected_wargame_id is not None
        else []
    )

    selected_edition_id = resolve_selected_edition(
        request,
        available_editions,
        editions_by_id,
    )

    stats_by_key, faction_list_ids = load_statistics(player)

    faction_lists = load_faction_lists(faction_list_ids)

    relevant_wargame_ids = (
        {selected_wargame_id}
        if selected_wargame_id is not None
        else set()
    )

    relevant_editions = (
        [editions_by_id[selected_edition_id]]
        if selected_edition_id is not None
        else []
    )

    statistics_rows_for_table = build_statistics_rows(
        faction_lists=faction_lists,
        stats_by_key=stats_by_key,
        player_faction_ids=player_faction_ids,
        relevant_wargame_ids=relevant_wargame_ids,
        relevant_editions=relevant_editions,
        wargames_by_id=wargames_by_id,
    )

    selected_wargame_label = (
        wargames_by_id[selected_wargame_id].name
        if selected_wargame_id is not None
        else "—"
    )

    selected_edition_label = (
        editions_by_id[selected_edition_id].edition_name
        if selected_edition_id is not None
        else "—"
    )

    games_page = request.args.get(
        "games_page",
        default=1,
        type=int,
    )

    games, games_page, games_pages, games_total = load_games(
        player,
        is_self,
        games_page,
    )

    game_ids = [game.id for game in games]

    conflict_ids_by_game = load_conflict_ids(game_ids)

    teams_by_game, players_by_team = load_teams_and_players(game_ids)

    if is_self:
        confirmations_by_game = load_confirmations(game_ids, player)
    else:
        confirmations_by_game = {}

    games_for_table = build_games_for_table(
        games=games,
        teams_by_game=teams_by_game,
        players_by_team=players_by_team,
        confirmations_by_game=confirmations_by_game,
        conflict_ids_by_game=conflict_ids_by_game,
        player=player,
        is_self=is_self,
    )

    has_pending = (
            is_self
            and has_pending_confirmations(player)
    )

    reviews_page = request.args.get(
        "page",
        default=1,
        type=int,
    )

    reviews, reviews_page, reviews_pages, reviews_total = load_reviews(
        player,
        reviews_page,
    )

    return render_template(
        "profile/view.html",
        player=player,
        is_self=is_self,
        rating=rating,
        rating_count=rating_count,
        wargames=wargames,
        editions_by_wargame=editions_by_wargame,
        available_editions=available_editions,
        selected_wargame_id=selected_wargame_id,
        selected_edition_id=selected_edition_id,
        selected_wargame_label=selected_wargame_label,
        selected_edition_label=selected_edition_label,
        statistics_rows_for_table=statistics_rows_for_table,
        games_for_table=games_for_table,
        games_page=games_page,
        games_pages=games_pages,
        games_total=games_total,
        reviews=reviews,
        reviews_page=reviews_page,
        reviews_pages=reviews_pages,
        reviews_total=reviews_total,
        has_pending=has_pending
    )


def load_player(nickname):
    player = Player.query.filter_by(nickname=nickname).first()

    if player is None:
        abort(404)

    return player


def load_rating(player):
    rating_row = (
        db.session.query(
            func.avg(Review.rating),
            func.count(Review.id),
        )
        .join(Game, Review.game_id == Game.id)
        .filter(
            Review.player_id == player.id,
            Game.status == "OFFICIAL",
        )
        .one()
    )

    rating_value, rating_count = rating_row

    if rating_count == 0 or rating_value is None:
        rating = None
    else:
        rating = round(float(rating_value), 1)

    return rating, rating_count


def load_player_factions(player):
    return (
        PlayerFaction.query
        .filter(PlayerFaction.player_id == player.id)
        .all()
    )


def load_wargames_and_editions(available_wargame_ids):
    wargames = (
        Wargame.query
        .filter(Wargame.id.in_(available_wargame_ids))
        .order_by(Wargame.name)
        .all()
        if available_wargame_ids
        else []
    )

    editions = (
        WargameEdition.query
        .order_by(
            WargameEdition.wargame_id,
            WargameEdition.id,
        )
        .all()
    )

    editions_by_wargame = {}

    for edition in editions:
        editions_by_wargame.setdefault(
            edition.wargame_id,
            [],
        ).append(edition)

    editions_by_id = {edition.id: edition for edition in editions}
    wargames_by_id = {wargame.id: wargame for wargame in wargames}

    return (
        wargames,
        editions,
        editions_by_wargame,
        editions_by_id,
        wargames_by_id,
    )


def resolve_selected_wargame(request, wargames_by_id):
    raw_value = request.args.get("wargame", "")

    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        parsed = None

    if parsed in wargames_by_id:
        return parsed

    if not wargames_by_id:
        return None

    return max(wargames_by_id.keys())


def resolve_selected_edition(request, available_editions, editions_by_id):
    raw_value = request.args.get("edition", "")

    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        parsed = None

    available_edition_ids = {
        edition.id
        for edition in available_editions
    }

    if parsed in available_edition_ids:
        return parsed

    if not available_editions:
        return None

    return max(edition.id for edition in available_editions)


def load_statistics(player):
    statistics_rows = (
        PlayerFactionStatistics.query
        .filter(PlayerFactionStatistics.player_id == player.id)
        .all()
    )

    stats_by_key = {}
    faction_list_ids = set()

    for row in statistics_rows:
        key = (row.faction_list_id, row.edition_id)

        stats_by_key[key] = {
            "game_count": row.game_count,
            "wins": row.wins,
            "losses": row.losses,
        }

        faction_list_ids.add(row.faction_list_id)

    return stats_by_key, faction_list_ids


def load_faction_lists(faction_list_ids):
    faction_lists = {}

    if not faction_list_ids:
        return faction_lists

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

    for faction_list_id, faction in items:
        faction_lists.setdefault(
            faction_list_id,
            [],
        ).append(faction)

    return faction_lists


def load_all_faction_list_ids():
    rows = (
        FactionListFaction.query
        .with_entities(FactionListFaction.faction_list_id)
        .distinct()
        .all()
    )

    return {row.faction_list_id for row in rows}


def load_faction_list_members(faction_list_id):
    return (
        db.session.query(Faction)
        .join(
            FactionListFaction,
            FactionListFaction.faction_id == Faction.id,
        )
        .filter(FactionListFaction.faction_list_id == faction_list_id)
        .all()
    )


def get_wargame_by_id(wargames_by_id, wargame_id):
    wargame = wargames_by_id.get(wargame_id)

    if wargame is None:
        wargame = Wargame.query.get(wargame_id)

    return wargame


def build_statistics_rows(
        faction_lists,
        stats_by_key,
        player_faction_ids,
        relevant_wargame_ids,
        relevant_editions,
        wargames_by_id,
):
    candidate_faction_list_ids = set()

    for faction_list_id, factions in faction_lists.items():
        if not factions:
            continue

        faction_wargame_ids = {
            faction.wargame_id
            for faction in factions
        }

        if not faction_wargame_ids.issubset(relevant_wargame_ids):
            continue

        if not all(
                faction.id in player_faction_ids
                for faction in factions
        ):
            continue

        candidate_faction_list_ids.add(faction_list_id)

    all_faction_list_ids = load_all_faction_list_ids()

    for faction_list_id in all_faction_list_ids:
        if faction_list_id in faction_lists:
            continue

        factions = load_faction_list_members(faction_list_id)

        if not factions:
            continue

        faction_wargame_ids = {
            faction.wargame_id
            for faction in factions
        }

        if not faction_wargame_ids.issubset(relevant_wargame_ids):
            continue

        if not all(
                faction.id in player_faction_ids
                for faction in factions
        ):
            continue

        faction_lists[faction_list_id] = factions
        candidate_faction_list_ids.add(faction_list_id)

    statistics_rows_for_table = []

    for faction_list_id in candidate_faction_list_ids:
        factions = faction_lists[faction_list_id]

        faction_names = " + ".join(
            sorted(
                faction.faction_name
                for faction in factions
            )
        )

        faction_wargame_ids = {
            faction.wargame_id
            for faction in factions
        }

        for edition in relevant_editions:
            if edition.wargame_id not in faction_wargame_ids:
                continue

            wargame = get_wargame_by_id(
                wargames_by_id,
                edition.wargame_id,
            )

            stats = stats_by_key.get(
                (faction_list_id, edition.id)
            )

            if stats is None:
                game_count = None
                wins = None
                losses = None
                draws = None
            else:
                game_count = stats["game_count"]
                wins = stats["wins"]
                losses = stats["losses"]

                draws = max(
                    0,
                    game_count - wins - losses,
                )

            statistics_rows_for_table.append(
                {
                    "wargame_name": wargame.name,
                    "wargame_id": wargame.id,
                    "edition_id": edition.id,
                    "faction_names": faction_names,
                    "game_count": game_count,
                    "wins": wins,
                    "losses": losses,
                    "draws": draws,
                }
            )

    statistics_rows_for_table.sort(
        key=lambda row: (
            row["wargame_name"],
            row["edition_id"],
            row["faction_names"],
        )
    )

    return statistics_rows_for_table


def has_pending_confirmations(player):
    return (
            db.session.query(GameConfirmation.id)
            .filter(
                GameConfirmation.player_id == player.id,
                GameConfirmation.response == "WAIT",
            )
            .first()
            is not None
    )


def load_games(player, is_self, page):
    games_query = (
        Game.query
        .join(Team, Team.game_id == Game.id)
        .join(PlayerGame, PlayerGame.team_id == Team.id)
        .filter(PlayerGame.player_id == player.id)
    )

    if not is_self:
        games_query = games_query.filter(Game.status == "OFFICIAL")

    games_total = games_query.count()

    games_pages = (
        (games_total + GAMES_PER_PAGE - 1) // GAMES_PER_PAGE
        if games_total > 0
        else 1
    )

    if page < 1:
        page = 1

    if page > games_pages:
        page = games_pages

    games = (
        games_query
        .order_by(Game.date.desc(), Game.id.desc())
        .limit(GAMES_PER_PAGE)
        .offset((page - 1) * GAMES_PER_PAGE)
        .distinct()
        .all()
    )

    return games, page, games_pages, games_total


def load_conflict_ids(game_ids):
    if not game_ids:
        return {}

    rows = (
        db.session.query(
            GameVersion.game_id,
            GameVersion.game_conflict_id,
        )
        .filter(GameVersion.game_id.in_(game_ids))
        .all()
    )

    return {
        game_id: conflict_id
        for game_id, conflict_id in rows
    }


def load_teams_and_players(game_ids):
    teams_by_game = {}
    players_by_team = {}

    if not game_ids:
        return teams_by_game, players_by_team

    teams = (
        Team.query
        .filter(Team.game_id.in_(game_ids))
        .order_by(Team.command_number)
        .all()
    )

    for team in teams:
        teams_by_game.setdefault(team.game_id, []).append(team)

    team_ids = [team.id for team in teams]

    if not team_ids:
        return teams_by_game, players_by_team

    player_games = (
        PlayerGame.query
        .filter(PlayerGame.team_id.in_(team_ids))
        .all()
    )

    for player_game in player_games:
        players_by_team.setdefault(
            player_game.team_id,
            [],
        ).append(player_game.player)

    return teams_by_game, players_by_team


def load_confirmations(game_ids, player):
    confirmations_by_game = {}

    if not game_ids:
        return confirmations_by_game

    confirmations = (
        GameConfirmation.query
        .filter(
            GameConfirmation.game_id.in_(game_ids),
            GameConfirmation.player_id == player.id,
        )
        .all()
    )

    for confirmation in confirmations:
        confirmations_by_game[confirmation.game_id] = confirmation

    return confirmations_by_game


def resolve_status_label(game, confirmation):
    if game.status == "PENDING":
        if confirmation is None:
            return "Ожидает вашего подтверждения"

        if confirmation.response == "CONFIRM":
            return "Ожидает подтверждения других игроков"

        if confirmation.response == "CONFLICT":
            return "На рассмотрении"

        return "Ожидает вашего подтверждения"

    if game.status == "OFFICIAL":
        return "Официальная"

    if game.status == "MODERATION":
        return "На рассмотрении"

    if game.status == "CANCELLED":
        return "Неофициальная"

    return game.status


def build_games_for_table(
        games,
        teams_by_game,
        players_by_team,
        confirmations_by_game,
        conflict_ids_by_game,
        player,
        is_self,
):
    games_for_table = []

    for game in games:
        teams = teams_by_game.get(game.id, [])

        participant_names = []

        for team in teams:
            for participant in players_by_team.get(team.id, []):
                participant_names.append(participant.nickname)

        participant_names.sort()

        game_name = ", ".join(participant_names)

        player_result = None

        for team in teams:
            for participant in players_by_team.get(team.id, []):
                if participant.id == player.id:
                    player_result = team.result
                    break

            if player_result is not None:
                break

        if is_self:
            status_label = resolve_status_label(
                game,
                confirmations_by_game.get(game.id),
            )
        else:
            status_label = None

        games_for_table.append(
            {
                "id": game.id,
                "name": game_name,
                "date": game.date,
                "wargame_name": game.edition.wargame.name,
                "edition_name": game.edition.edition_name,
                "roster_points": game.roster_points,
                "result": player_result,
                "status_label": status_label,
                "status": game.status,
                "conflict_id": conflict_ids_by_game.get(game.id),
            }
        )

    return games_for_table


def load_reviews(player, page):
    reviews_query = (
        Review.query
        .join(Game, Review.game_id == Game.id)
        .filter(
            Review.player_id == player.id,
            Game.status == "OFFICIAL",
        )
    )

    reviews_total = reviews_query.count()

    reviews_pages = (
        (reviews_total + REVIEWS_PER_PAGE - 1) // REVIEWS_PER_PAGE
        if reviews_total > 0
        else 1
    )

    if page < 1:
        page = 1

    if page > reviews_pages:
        page = reviews_pages

    reviews = (
        reviews_query
        .order_by(Review.created_at.desc())
        .limit(REVIEWS_PER_PAGE)
        .offset((page - 1) * REVIEWS_PER_PAGE)
        .all()
    )

    return reviews, page, reviews_pages, reviews_total
