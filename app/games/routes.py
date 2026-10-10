from datetime import datetime

from flask import (
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from app.auth.decorators import login_required
from app.extensions import db
from app.games import games_bp
from app.services.game_creation import (
    build_form_snapshot,
    find_or_create_faction_list,
    load_form_context,
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
    Team,
    Wargame,
    WargameEdition,
)
from app.services.game_data import load_version_data, load_game_reviews, load_list_participants

RESULT_LABELS = {
    "WIN": "Победа",
    "LOSS": "Поражение",
    "DRAW": "Ничья",
}

PER_PAGE = 30


def result_label(value):
    if value is None:
        return "—"

    return RESULT_LABELS.get(value, value)


def render_new_form(error=None, form_data=None):
    context = load_form_context()

    return render_template(
        "games/new.html",
        error=error,
        form_data=form_data or {},
        **context,
    )


@games_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if g.current_user.is_blocked:
        flash("Вы заблокированы для создания партий.")
        return redirect(
            url_for(
                "profile.view",
                nickname=g.current_user.nickname,
            )
        )
    if request.method == "GET":
        return render_new_form()

    form = request.form

    wargame_id = form.get("wargame", type=int)
    edition_id = form.get("edition", type=int)
    date_value = form.get("date", "").strip()
    roster_points = form.get("roster_points", type=int)

    if not wargame_id:
        return render_new_form("Выберите варгейм.")

    if not edition_id:
        return render_new_form("Выберите редакцию.")

    if not date_value:
        return render_new_form("Укажите дату партии.")

    if roster_points is None or roster_points <= 0:
        return render_new_form("Формат игры должен быть больше нуля.")

    wargame = db.session.get(Wargame, wargame_id)

    if wargame is None:
        return render_new_form("Выбранный варгейм не найден.")

    edition = db.session.get(WargameEdition, edition_id)

    if edition is None or edition.wargame_id != wargame.id:
        return render_new_form("Выбранная редакция не относится к варгейму.")

    try:
        game_date = datetime.strptime(date_value, "%Y-%m-%d").date()
    except ValueError:
        return render_new_form("Некорректный формат даты.")

    teams = parse_teams_form(form)

    snapshot = build_form_snapshot(form)

    if len(teams) < 2:
        return render_new_form(
            "Партия должна содержать минимум 2 команды.",
            snapshot,
        )

    all_player_ids = []
    parsed_teams_raw = []

    for team_index, team in teams.items():
        players = team.get("players", [])

        if not players:
            return render_new_form(
                f"В команде {team_index + 1} нет игроков.",
                snapshot,
            )

        team_players = []

        for player_data in players:
            player_id = player_data.get("id")

            try:
                player_id = int(player_id)
            except (TypeError, ValueError):
                return render_new_form(
                    f"Некорректный игрок в команде {team_index + 1}.",
                    snapshot,
                )

            faction_ids = player_data.get("factions", [])

            if not faction_ids:
                return render_new_form(
                    f"У игрока в команде {team_index + 1} "
                    f"не выбрана фракция.",
                    snapshot,
                )

            try:
                faction_ids = [int(fid) for fid in faction_ids]
            except (TypeError, ValueError):
                return render_new_form(
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
        return render_new_form(
            "Один или несколько игроков не найдены.",
            snapshot,
        )

    if len(set(all_player_ids)) != len(all_player_ids):
        return render_new_form(
            "Один игрок не может участвовать в партии дважды.",
            snapshot,
        )

    if g.current_user.id not in all_player_ids:
        return render_new_form(
            "Создатель партии должен быть её участником.",
            snapshot,
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
                return render_new_form(
                    f"Некорректные очки в команде {team_index + 1}.",
                    snapshot,
                )

            if score < 0:
                return render_new_form(
                    "Очки команды не могут быть отрицательными.",
                    snapshot,
                )

        result = team.get("result", "").strip() or None

        if result not in (None, "WIN", "LOSS", "DRAW"):
            return render_new_form(
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
        return render_new_form(
            "Одна или несколько фракций не найдены.",
            snapshot,
        )

    factions_by_id = {faction.id: faction for faction in factions}

    for team in parsed_teams:
        for player_data in team["players"]:
            for faction_id in player_data["faction_ids"]:
                faction = factions_by_id[faction_id]

                if faction.wargame_id != wargame.id:
                    return render_new_form(
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
            return render_new_form(
                "Очки команд равны, но победитель указан явно.",
                snapshot,
            )

        if implied_result == "WIN" and explicit_draw:
            return render_new_form(
                "Указана ничья, но очки команд не равны.",
                snapshot,
            )

        if implied_result == "WIN" and explicit_winner is not None:
            if explicit_winner is not top_teams[0]:
                return render_new_form(
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
        win_count = sum(
            1 for team in parsed_teams
            if team["result"] == "WIN"
        )

        if win_count > 1:
            return render_new_form(
                "Победителем партии может быть только одна команда. "
                "Если победитель не определён, укажите ничью для всех команд.",
                snapshot,
            )

        draw_count = sum(
            1 for team in parsed_teams
            if team["result"] == "DRAW"
        )

        if draw_count > 0 and win_count > 0:
            return render_new_form(
                "Нельзя одновременно указать победителя и ничью.",
                snapshot,
            )

        if draw_count > 0 and draw_count != len(parsed_teams):
            return render_new_form(
                "Если указана ничья, её должны получить все команды.",
                snapshot,
            )

        for team in parsed_teams:
            if team["result"] is None:
                team["result"] = "LOSS"

    game = Game(
        command_count=len(parsed_teams),
        roster_points=roster_points,
        status="PENDING",
        date=game_date,
        edition_id=edition.id,
        created_by=g.current_user.id,
    )

    db.session.add(game)
    db.session.flush()

    for team_data in parsed_teams:
        team = Team(
            game_id=game.id,
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

    conflict = GameConflict(
        original_game_id=game.id,
        status="OPEN",
    )

    db.session.add(conflict)
    db.session.flush()

    db.session.add(
        GameVersion(
            game_conflict_id=conflict.id,
            game_id=game.id,
        )
    )

    for player_id in all_player_ids:
        response = (
            "CONFIRM"
            if player_id == g.current_user.id
            else "WAIT"
        )

        db.session.add(
            GameConfirmation(
                game_id=game.id,
                player_id=player_id,
                response=response,
            )
        )

    db.session.commit()

    return redirect(
        url_for(
            "confirm.view",
            conflict_id=conflict.id,
        )
    )


@games_bp.route("/search_players")
@login_required
def search_players():
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify([])

    players = (
        Player.query
        .filter(Player.nickname.ilike(f"%{query}%"))
        .order_by(Player.nickname)
        .limit(10)
        .all()
    )

    return jsonify([
        {
            "id": player.id,
            "nickname": player.nickname,
        }
        for player in players
    ])


@games_bp.route("/<int:game_id>")
@login_required
def view(game_id):
    game = db.session.get(Game, game_id)

    if game is None:
        abort(404)

    if game.status != "OFFICIAL":
        abort(404)

    version_data = load_version_data(game)
    reviews = load_game_reviews(game)

    return render_template(
        "games/view.html",
        game=game,
        version_data=version_data,
        reviews=reviews,
        creator=game.creator,
        result_label=result_label,
    )


@games_bp.route("/")
@login_required
def list_games():
    wargames = (
        Wargame.query
        .order_by(Wargame.name)
        .all()
    )

    selected_wargame_id = request.args.get("wargame", type=int)

    wargame_ids = {wargame.id for wargame in wargames}

    if selected_wargame_id not in wargame_ids:
        selected_wargame_id = None

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

    if selected_wargame_id is not None:
        available_editions = editions_by_wargame.get(
            selected_wargame_id,
            [],
        )
    else:
        available_editions = editions

    available_edition_ids = {
        edition.id for edition in available_editions
    }

    selected_edition_id = request.args.get("edition", type=int)

    if selected_edition_id not in available_edition_ids:
        selected_edition_id = None

    date_raw = request.args.get("date", "").strip()

    selected_date = None

    if date_raw:
        try:
            selected_date = date_type.fromisoformat(date_raw)
        except ValueError:
            selected_date = None

    page = request.args.get("page", default=1, type=int)

    query = (
        Game.query
        .filter(Game.status == "OFFICIAL")
    )

    if selected_wargame_id is not None:
        query = query.join(
            WargameEdition,
            WargameEdition.id == Game.edition_id,
        ).filter(
            WargameEdition.wargame_id == selected_wargame_id
        )

    if selected_edition_id is not None:
        query = query.filter(
            Game.edition_id == selected_edition_id
        )

    if selected_date is not None:
        query = query.filter(Game.date == selected_date)

    query = query.order_by(
        Game.date.desc(),
        Game.id.desc(),
    )

    total_count = query.count()
    total_pages = max(1, (total_count + PER_PAGE - 1) // PER_PAGE)

    if page < 1:
        page = 1

    if page > total_pages:
        page = total_pages

    games = (
        query
        .limit(PER_PAGE)
        .offset((page - 1) * PER_PAGE)
        .all()
    )

    game_ids = [game.id for game in games]

    participants_by_game = load_list_participants(game_ids)

    rows = []

    for game in games:
        rows.append({
            "game": game,
            "wargame_name": game.edition.wargame.name,
            "edition_name": game.edition.edition_name,
            "participants": participants_by_game.get(game.id, []),
        })

    return render_template(
        "games/list.html",
        rows=rows,
        wargames=wargames,
        available_editions=available_editions,
        selected_wargame_id=selected_wargame_id,
        selected_edition_id=selected_edition_id,
        selected_date=selected_date,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
    )