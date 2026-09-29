from datetime import datetime

from flask import (
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from app.auth.decorators import login_required
from app.confirm import confirm_bp
from app.extensions import db
from app.games.services import (
    build_form_snapshot,
    find_or_create_faction_list,
    form_to_json,
    parse_teams_form,
)
from app.models import (
    Faction,
    Game,
    GameConfirmation,
    GameConflict,
    GameFaction,
    GameVersion,
    Player,
    PlayerGame,
    Review,
    Team,
    Wargame,
    WargameEdition, PlayerFactionStatistics,
)

STATUS_LABELS = {
    "PENDING": "Ожидает подтверждения",
    "OFFICIAL": "Официальная",
    "CANCELLED": "Неофициальная",
    "MODERATION": "На рассмотрении",
}

RESPONSE_LABELS = {
    "CONFIRM": "Подтверждено",
    "CONFLICT": "Оспорено",
    "WAIT": "Ожидает решения",
}

RESULT_LABELS = {
    "WIN": "Победа",
    "LOSS": "Поражение",
    "DRAW": "Ничья",
}


def result_label(value):
    if value is None:
        return "—"

    return RESULT_LABELS.get(value, value)


@confirm_bp.route("/<int:conflict_id>")
@login_required
def view(conflict_id):
    conflict = db.session.get(GameConflict, conflict_id)

    if conflict is None:
        abort(404)

    versions = load_versions(conflict)

    if not versions:
        abort(404)

    for version in versions:
        if version["game"].status == "OFFICIAL":
            return redirect(
                url_for(
                    "games.view",
                    game_id=version["game"].id,
                )
            )

    is_participant = is_user_participant(conflict, g.current_user.id)
    is_moderator = g.current_user.role in ("MODERATOR", "ADMIN")

    if not is_participant and not is_moderator:
        abort(403)

    total_pages = len(versions)

    page = request.args.get("page", default=1, type=int)

    if page < 1:
        page = 1

    if page > total_pages:
        page = total_pages

    current_version = versions[page - 1]
    current_game = current_version["game"]

    version_data = load_version_data(current_game)

    confirmations_by_game = load_own_confirmations(
        [v["game"].id for v in versions],
        g.current_user,
    )

    for version in versions:
        version["response"] = confirmations_by_game.get(
            version["game"].id
        )

    can_act = (
        is_participant
        and current_version["response"] is None
    ) or (
        is_participant
        and current_version["response"].response == "WAIT"
    )

    own_reviews = load_own_reviews(conflict, g.current_user)
    review_targets = load_review_targets(conflict, g.current_user)

    status_label = STATUS_LABELS.get(
        current_game.status,
        current_game.status,
    )

    response_label = None

    if current_version["response"] is not None:
        response_label = RESPONSE_LABELS.get(
            current_version["response"].response,
            current_version["response"].response,
        )

    return render_template(
        "confirm/view.html",
        conflict=conflict,
        versions=versions,
        current_version=current_version,
        current_page=page,
        total_pages=total_pages,
        version_data=version_data,
        own_reviews=own_reviews,
        review_targets=review_targets,
        can_act=can_act,
        is_participant=is_participant,
        status_label=status_label,
        response_label=response_label,
        result_label=result_label,
    )
@confirm_bp.route("/<int:conflict_id>/confirm", methods=["POST"])
@login_required
def confirm_version(conflict_id):
    conflict = db.session.get(GameConflict, conflict_id)

    if conflict is None:
        abort(404)

    version_id = request.form.get("version", type=int)

    if version_id is None:
        abort(400)

    versions = load_versions(conflict)

    version_ids = [version["game"].id for version in versions]

    if version_id not in version_ids:
        abort(400)

    selected_game = db.session.get(Game, version_id)

    if selected_game is not None and selected_game.status == "OFFICIAL":
        return redirect(
            url_for(
                "games.view",
                game_id=selected_game.id,
            )
        )

    is_participant = is_user_participant(conflict, g.current_user.id)

    if not is_participant:
        abort(403)

    confirmations = (
        GameConfirmation.query
        .filter(
            GameConfirmation.game_id.in_(version_ids),
            GameConfirmation.player_id == g.current_user.id,
        )
        .all()
    )

    confirmations_by_game = {
        confirmation.game_id: confirmation
        for confirmation in confirmations
    }

    for game_id in version_ids:
        confirmation = confirmations_by_game.get(game_id)

        if confirmation is None:
            confirmation = GameConfirmation(
                game_id=game_id,
                player_id=g.current_user.id,
                response="WAIT",
            )
            db.session.add(confirmation)
            confirmations_by_game[game_id] = confirmation

        if game_id == version_id:
            confirmation.response = "CONFIRM"
        else:
            confirmation.response = "CONFLICT"

    db.session.commit()

    finalized_game_id = try_finalize(conflict)

    if finalized_game_id is not None:
        db.session.commit()

        return redirect(
            url_for(
                "games.view",
                game_id=finalized_game_id,
            )
        )

    return redirect(
        url_for(
            "confirm.view",
            conflict_id=conflict.id,
            page=_find_page_of_version(versions, version_id),
        )
    )


@confirm_bp.route("/<int:conflict_id>/review", methods=["POST"])
@login_required
def add_review(conflict_id):
    conflict = db.session.get(GameConflict, conflict_id)

    if conflict is None:
        abort(404)

    is_participant = is_user_participant(conflict, g.current_user.id)

    if not is_participant:
        abort(403)

    player_id = request.form.get("player_id", type=int)
    rating = request.form.get("rating", type=int)
    text = request.form.get("text", "").strip() or None

    if player_id is None:
        abort(400)

    if rating is None or rating < 1 or rating > 5:
        abort(400)

    if player_id == g.current_user.id:
        abort(400)

    review_targets = load_review_targets(conflict, g.current_user)
    target_ids = {target["player"].id for target in review_targets}

    if player_id not in target_ids:
        abort(400)

    existing_review = (
        Review.query
        .filter(
            Review.game_id == conflict.original_game_id,
            Review.author == g.current_user.id,
            Review.player_id == player_id,
        )
        .first()
    )

    if existing_review is not None:
        abort(400)

    review = Review(
        game_id=conflict.original_game_id,
        player_id=player_id,
        author=g.current_user.id,
        rating=rating,
        text=text,
    )

    db.session.add(review)
    db.session.commit()

    return redirect(
        url_for(
            "confirm.view",
            conflict_id=conflict.id,
        )
    )

@confirm_bp.route("/<int:conflict_id>/conflict", methods=["GET", "POST"])
@login_required
def conflict_version(conflict_id):
    conflict = db.session.get(GameConflict, conflict_id)

    if conflict is None:
        abort(404)

    is_participant = is_user_participant(conflict, g.current_user.id)

    if not is_participant:
        abort(403)

    if user_has_version(conflict, g.current_user.id):
        flash("У вас уже есть версия в этом конфликте.")
        return redirect(
            url_for(
                "confirm.view",
                conflict_id=conflict.id,
            )
        )

    versions = load_versions(conflict)

    if not versions:
        abort(404)

    total_pages = len(versions)

    page = request.args.get("page", default=1, type=int)

    if page < 1:
        page = 1

    if page > total_pages:
        page = total_pages

    source_version = versions[page - 1]

    if request.method == "GET":
        source_game = source_version["game"]
        form_data = build_form_data_from_game(source_game)
        context = load_form_context()

        return render_template(
            "confirm/version.html",
            conflict=conflict,
            source_version=source_version,
            source_page=page,
            form_data=form_data,
            **context,
        )

    return handle_conflict_post(conflict, source_version, page)

def handle_conflict_post(conflict, source_version, source_page):
    form = request.form

    snapshot = form_to_json(form)

    wargame_id = form.get("wargame", type=int)
    edition_id = form.get("edition", type=int)
    date_value = form.get("date", "").strip()
    roster_points = form.get("roster_points", type=int)

    if not wargame_id:
        return render_conflict_form(
            conflict, source_version, source_page,
            "Выберите варгейм.", snapshot,
        )

    if not edition_id:
        return render_conflict_form(
            conflict, source_version, source_page,
            "Выберите редакцию.", snapshot,
        )

    if not date_value:
        return render_conflict_form(
            conflict, source_version, source_page,
            "Укажите дату партии.", snapshot,
        )

    if roster_points is None or roster_points <= 0:
        return render_conflict_form(
            conflict, source_version, source_page,
            "Формат игры должен быть больше нуля.", snapshot,
        )

    wargame = db.session.get(Wargame, wargame_id)

    if wargame is None:
        return render_conflict_form(
            conflict, source_version, source_page,
            "Выбранный варгейм не найден.", snapshot,
        )

    edition = db.session.get(WargameEdition, edition_id)

    if edition is None or edition.wargame_id != wargame.id:
        return render_conflict_form(
            conflict, source_version, source_page,
            "Выбранная редакция не относится к варгейму.", snapshot,
        )

    try:
        game_date = datetime.strptime(date_value, "%Y-%m-%d").date()
    except ValueError:
        return render_conflict_form(
            conflict, source_version, source_page,
            "Некорректный формат даты.", snapshot,
        )

    teams = parse_teams_form(form)

    if len(teams) < 2:
        return render_conflict_form(
            conflict, source_version, source_page,
            "Партия должна содержать минимум 2 команды.", snapshot,
        )

    all_player_ids = []
    parsed_teams_raw = []

    for team_index, team in teams.items():
        players = team.get("players", [])

        if not players:
            return render_conflict_form(
                conflict, source_version, source_page,
                f"В команде {team_index + 1} нет игроков.", snapshot,
            )

        team_players = []

        for player_data in players:
            player_id = player_data.get("id")

            try:
                player_id = int(player_id)
            except (TypeError, ValueError):
                return render_conflict_form(
                    conflict, source_version, source_page,
                    f"Некорректный игрок в команде {team_index + 1}.",
                    snapshot,
                )

            faction_ids = player_data.get("factions", [])

            if not faction_ids:
                return render_conflict_form(
                    conflict, source_version, source_page,
                    f"У игрока в команде {team_index + 1} "
                    f"не выбрана фракция.",
                    snapshot,
                )

            try:
                faction_ids = [int(fid) for fid in faction_ids]
            except (TypeError, ValueError):
                return render_conflict_form(
                    conflict, source_version, source_page,
                    f"Некорректная фракция в команде {team_index + 1}.",
                    snapshot,
                )

            team_players.append({
                "player_id": player_id,
                "faction_ids": faction_ids,
            })

            all_player_ids.append(player_id)

        parsed_teams_raw.append({
            "team_index": team_index,
            "team": team,
            "players": team_players,
        })

    players = (
        Player.query
        .filter(Player.id.in_(all_player_ids))
        .all()
        if all_player_ids
        else []
    )

    players_by_id = {player.id: player for player in players}

    snapshot = build_form_snapshot(form, players_by_id)

    if len(players) != len(set(all_player_ids)):
        return render_conflict_form(
            conflict, source_version, source_page,
            "Один или несколько игроков не найдены.", snapshot,
        )

    if len(set(all_player_ids)) != len(all_player_ids):
        return render_conflict_form(
            conflict, source_version, source_page,
            "Один игрок не может участвовать в партии дважды.", snapshot,
        )

    if g.current_user.id not in all_player_ids:
        return render_conflict_form(
            conflict, source_version, source_page,
            "Создатель версии должен быть её участником.", snapshot,
        )

    parsed_teams = []

    for item in parsed_teams_raw:
        team = item["team"]
        team_index = item["team_index"]

        score_raw = team.get("score", "").strip()

        if score_raw == "":
            score = None
        else:
            try:
                score = int(score_raw)
            except ValueError:
                return render_conflict_form(
                    conflict, source_version, source_page,
                    f"Некорректные очки в команде {team_index + 1}.",
                    snapshot,
                )

            if score < 0:
                return render_conflict_form(
                    conflict, source_version, source_page,
                    "Очки команды не могут быть отрицательными.",
                    snapshot,
                )

        result = team.get("result", "").strip() or None

        if result not in (None, "WIN", "LOSS", "DRAW"):
            return render_conflict_form(
                conflict, source_version, source_page,
                f"Некорректный результат в команде {team_index + 1}.",
                snapshot,
            )

        team_name = team.get("name", "").strip()

        if not team_name:
            team_name = f"Команда {team_index + 1}"

        parsed_teams.append({
            "name": team_name,
            "command_number": team_index + 1,
            "score": score,
            "result": result,
            "players": item["players"],
        })

    all_faction_ids = set()

    for team in parsed_teams:
        for player_data in team["players"]:
            all_faction_ids.update(player_data["faction_ids"])

    factions = (
        Faction.query
        .filter(Faction.id.in_(all_faction_ids))
        .all()
        if all_faction_ids
        else []
    )

    if len(factions) != len(all_faction_ids):
        return render_conflict_form(
            conflict, source_version, source_page,
            "Одна или несколько фракций не найдены.", snapshot,
        )

    factions_by_id = {faction.id: faction for faction in factions}

    for team in parsed_teams:
        for player_data in team["players"]:
            for faction_id in player_data["faction_ids"]:
                faction = factions_by_id[faction_id]

                if faction.wargame_id != wargame.id:
                    return render_conflict_form(
                        conflict, source_version, source_page,
                        f"Фракция «{faction.faction_name}» "
                        f"не относится к выбранному варгейму.",
                        snapshot,
                    )

    results = {
        team["result"]
        for team in parsed_teams
        if team["result"] is not None
    }

    scores = [team["score"] for team in parsed_teams]
    all_scores_set = all(score is not None for score in scores)

    if results and all_scores_set:
        max_score = max(scores)

        top_teams = [
            team for team in parsed_teams
            if team["score"] == max_score
        ]

        implied_result = "DRAW" if len(top_teams) > 1 else "WIN"

        explicit_winner = None

        for team in parsed_teams:
            if team["result"] == "WIN":
                explicit_winner = team
                break

        explicit_draw = any(
            team["result"] == "DRAW"
            for team in parsed_teams
        )

        if implied_result == "DRAW" and not explicit_draw:
            return render_conflict_form(
                conflict, source_version, source_page,
                "Очки команд равны, но победитель указан явно.",
                snapshot,
            )

        if implied_result == "WIN" and explicit_draw:
            return render_conflict_form(
                conflict, source_version, source_page,
                "Указана ничья, но очки команд не равны.",
                snapshot,
            )

        if implied_result == "WIN" and explicit_winner is not None:
            if explicit_winner is not top_teams[0]:
                return render_conflict_form(
                    conflict, source_version, source_page,
                    "Указанный победитель не совпадает "
                    "с командой с наибольшими очками.",
                    snapshot,
                )

    if not results and all_scores_set:
        max_score = max(scores)

        top_teams = [
            team for team in parsed_teams
            if team["score"] == max_score
        ]

        if len(top_teams) > 1:
            for team in parsed_teams:
                team["result"] = "DRAW"
        else:
            for team in parsed_teams:
                if team is top_teams[0]:
                    team["result"] = "WIN"
                else:
                    team["result"] = "LOSS"

    if results and not all_scores_set:
        for team in parsed_teams:
            if team["result"] is None:
                team["result"] = "LOSS"

    # === Снимок старых версий до создания новой ===

    old_versions = load_versions(conflict)
    old_version_ids = [v["game"].id for v in old_versions]
    old_author_ids = {v["game"].created_by for v in old_versions}

    # === Создание новой версии ===

    new_game = Game(
        command_count=len(parsed_teams),
        roster_points=roster_points,
        status="MODERATION",
        date=game_date,
        edition_id=edition.id,
        created_by=g.current_user.id,
    )

    db.session.add(new_game)
    db.session.flush()

    for team_data in parsed_teams:
        team = Team(
            game_id=new_game.id,
            name=team_data["name"],
            command_number=team_data["command_number"],
            result=team_data["result"],
            score=team_data["score"],
        )

        db.session.add(team)
        db.session.flush()

        for player_data in team_data["players"]:
            player_game = PlayerGame(
                player_id=player_data["player_id"],
                team_id=team.id,
            )

            db.session.add(player_game)
            db.session.flush()

            for faction_id in player_data["faction_ids"]:
                db.session.add(
                    GameFaction(
                        player_game_id=player_game.id,
                        faction_id=faction_id,
                    )
                )

            find_or_create_faction_list(player_data["faction_ids"])

    db.session.add(
        GameVersion(
            game_conflict_id=conflict.id,
            game_id=new_game.id,
        )
    )

    # === GameConfirmation для новой версии ===

    for player_id in all_player_ids:
        if player_id == g.current_user.id:
            response = "CONFIRM"
        elif player_id in old_author_ids:
            response = "CONFLICT"
        else:
            response = "WAIT"

        db.session.add(
            GameConfirmation(
                game_id=new_game.id,
                player_id=player_id,
                response=response,
            )
        )

    # === GameConfirmation автора новой версии для старых версий ===

    old_confirmations = (
        GameConfirmation.query
        .filter(
            GameConfirmation.game_id.in_(old_version_ids),
            GameConfirmation.player_id == g.current_user.id,
        )
        .all()
    )

    for confirmation in old_confirmations:
        confirmation.response = "CONFLICT"

    # === Перевод оригинала в MODERATION ===

    if conflict.original_game_id:
        original_game = db.session.get(Game, conflict.original_game_id)

        if original_game is not None:
            original_game.status = "MODERATION"

    db.session.commit()

    finalized_game_id = try_finalize(conflict)

    if finalized_game_id is not None:
        db.session.commit()

        return redirect(
            url_for(
                "games.view",
                game_id=finalized_game_id,
            )
        )

    new_versions = load_versions(conflict)
    new_page = len(new_versions)

    return redirect(
        url_for(
            "confirm.view",
            conflict_id=conflict.id,
            page=new_page,
        )
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


def _is_own_version(game_id, user_id):
    game = db.session.get(Game, game_id)

    if game is None:
        return False

    return game.created_by == user_id


def _find_page_of_version(versions, version_id):
    for index, version in enumerate(versions):
        if version["game"].id == version_id:
            return index + 1

    return 1


def load_version_author_ids(conflict):
    rows = (
        db.session.query(Game.created_by)
        .join(GameVersion, GameVersion.game_id == Game.id)
        .filter(GameVersion.game_conflict_id == conflict.id)
        .distinct()
        .all()
    )

    return {row[0] for row in rows}


def is_user_participant(conflict, user_id):
    game_ids = [
        version["game"].id
        for version in load_versions(conflict)
    ]

    if not game_ids:
        return False

    return (
            db.session.query(PlayerGame.id)
            .join(Team, Team.id == PlayerGame.team_id)
            .filter(
                Team.game_id.in_(game_ids),
                PlayerGame.player_id == user_id,
            )
            .first()
            is not None
    )


def user_has_version(conflict, user_id):
    return (
            db.session.query(Game.id)
            .join(GameVersion, GameVersion.game_id == Game.id)
            .filter(
                GameVersion.game_conflict_id == conflict.id,
                Game.created_by == user_id,
            )
            .first()
            is not None
    )


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


def build_form_data_from_game(game):
    teams = (
        Team.query
        .filter(Team.game_id == game.id)
        .order_by(Team.command_number)
        .all()
    )

    form_data = {
        "wargame": str(game.edition.wargame_id),
        "edition": str(game.edition_id),
        "date": game.date.strftime("%Y-%m-%d"),
        "roster_points": str(game.roster_points),
    }

    for team_index, team in enumerate(teams):
        form_data[f"teams[{team_index}][name]"] = team.name
        form_data[f"teams[{team_index}][score]"] = (
            str(team.score) if team.score is not None else ""
        )
        form_data[f"teams[{team_index}][result]"] = team.result or ""

        player_games = (
            PlayerGame.query
            .filter(PlayerGame.team_id == team.id)
            .all()
        )

        for player_index, player_game in enumerate(player_games):
            form_data[
                f"teams[{team_index}][players][{player_index}][id]"
            ] = str(player_game.player_id)

            form_data[
                f"teams[{team_index}][players][{player_index}][nickname]"
            ] = player_game.player.nickname

            factions = (
                GameFaction.query
                .filter(GameFaction.player_game_id == player_game.id)
                .all()
            )

            faction_ids = [str(gf.faction_id) for gf in factions]

            if len(faction_ids) == 1:
                form_data[
                    f"teams[{team_index}][players][{player_index}][factions][]"
                ] = faction_ids[0]
            else:
                form_data[
                    f"teams[{team_index}][players][{player_index}][factions][]"
                ] = faction_ids

    return form_data


def render_conflict_form(
        conflict,
        source_version,
        source_page,
        error,
        form_data,
):
    context = load_form_context()

    return render_template(
        "confirm/version.html",
        conflict=conflict,
        source_version=source_version,
        source_page=source_page,
        form_data=form_data,
        error=error,
        **context,
    )


def load_form_context():
    wargames = (
        Wargame.query
        .order_by(Wargame.name)
        .all()
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
        ).append({
            "id": edition.id,
            "edition_name": edition.edition_name,
        })

    factions = (
        Faction.query
        .order_by(
            Faction.wargame_id,
            Faction.faction_name,
        )
        .all()
    )

    factions_by_wargame = {}

    for faction in factions:
        factions_by_wargame.setdefault(
            faction.wargame_id,
            [],
        ).append({
            "id": faction.id,
            "faction_name": faction.faction_name,
        })

    return {
        "wargames": wargames,
        "editions_by_wargame": editions_by_wargame,
        "factions_by_wargame": factions_by_wargame,
    }
