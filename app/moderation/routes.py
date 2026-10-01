from flask import (
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from app.auth.decorators import moderator_required
from app.extensions import db
from app.models import (
    Game,
    GameConflict,
    GameVersion,
    PlayerGame,
    Team,
)
from app.moderation import moderation_bp
from app.services.game_data import (
    load_versions,
    load_version_data,
)
from app.moderation.services import (
    cancel_conflict,
    cancel_official_game,
    clear_review_text,
    finalize_by_moderator,
    restore_official_game,
    acquire_lock,
    is_locked_by_other,
    release_lock,
    update_lock_heartbeat,
    is_lock_expired
)
from app.models import Review

STATUS_LABELS = {
    "PENDING": "Ожидает подтверждения",
    "OFFICIAL": "Официальная",
    "CANCELLED": "Неофициальная",
    "MODERATION": "На рассмотрении",
}

RESULT_LABELS = {
    "WIN": "Победа",
    "LOSS": "Поражение",
    "DRAW": "Ничья",
}

PER_PAGE = 20


@moderation_bp.route("/")
@moderator_required
def index():
    conflicts, conflicts_page, conflicts_pages, conflicts_total = (
        load_open_conflicts(
            request.args.get("conflicts_page", default=1, type=int)
        )
    )

    games, games_page, games_pages, games_total = load_last_games(
        request.args.get("games_page", default=1, type=int)
    )

    return render_template(
        "moderation/index.html",
        conflicts=conflicts,
        conflicts_page=conflicts_page,
        conflicts_pages=conflicts_pages,
        conflicts_total=conflicts_total,
        games=games,
        games_page=games_page,
        games_pages=games_pages,
        games_total=games_total,
    )


def load_open_conflicts(page):
    query = (
        GameConflict.query
        .filter(GameConflict.status == "OPEN")
        .order_by(GameConflict.created_at.desc())
    )

    total = query.count()
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)

    if page < 1:
        page = 1

    if page > pages:
        page = pages

    conflicts = (
        query
        .limit(PER_PAGE)
        .offset((page - 1) * PER_PAGE)
        .all()
    )

    rows = []

    for conflict in conflicts:
        rows.append(build_conflict_row(conflict))

    return rows, page, pages, total


def build_conflict_row(conflict):
    original_game = db.session.get(Game, conflict.original_game_id)

    if original_game is None:
        return {
            "id": conflict.id,
            "original_game_id": None,
            "date": None,
            "wargame_name": "—",
            "edition_name": "—",
            "participants": [],
            "versions_count": 0,
        }

    participants = load_participants(original_game)

    versions_count = (
        GameVersion.query
        .filter(GameVersion.game_conflict_id == conflict.id)
        .count()
    )

    return {
        "id": conflict.id,
        "original_game_id": original_game.id,
        "date": original_game.date,
        "wargame_name": original_game.edition.wargame.name,
        "edition_name": original_game.edition.edition_name,
        "participants": participants,
        "versions_count": versions_count,
    }


def load_participants(game):
    teams = (
        Team.query
        .filter(Team.game_id == game.id)
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

    seen = set()
    participants = []

    for player_game in player_games:
        player_id = player_game.player_id

        if player_id in seen:
            continue

        seen.add(player_id)
        participants.append(player_game.player.nickname)

    participants.sort()

    return participants


def load_last_games(page):
    query = (
        Game.query
        .filter(Game.status.in_(["OFFICIAL", "CANCELLED"]))
        .order_by(Game.date.desc(), Game.id.desc())
    )

    total = query.count()
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)

    if page < 1:
        page = 1

    if page > pages:
        page = pages

    games = (
        query
        .limit(PER_PAGE)
        .offset((page - 1) * PER_PAGE)
        .all()
    )

    rows = []

    for game in games:
        rows.append({
            "id": game.id,
            "date": game.date,
            "wargame_name": game.edition.wargame.name,
            "edition_name": game.edition.edition_name,
            "creator_nickname": game.creator.nickname,
            "status": game.status,
            "participants": load_participants(game),
        })

    return rows, page, pages, total


def result_label(value):
    if value is None:
        return "—"

    return RESULT_LABELS.get(value, value)


@moderation_bp.route("/<int:conflict_id>")
@moderator_required
def conflict_view(conflict_id):
    conflict = db.session.get(GameConflict, conflict_id)

    if conflict is None:
        abort(404)

    if conflict.status != "OPEN":
        flash("Эта партия уже обработана.")
        return redirect(url_for("moderation.index"))

    if is_locked_by_other(conflict, g.current_user):
        return render_template(
            "moderation/locked.html",
            conflict=conflict,
            viewer=conflict.viewer,
            viewed_at=conflict.viewed_at,
        )

    acquire_lock(conflict, g.current_user)
    db.session.commit()

    versions = load_versions(conflict)

    if not versions:
        abort(404)

    total_pages = len(versions)

    page = request.args.get("page", default=1, type=int)

    if page < 1:
        page = 1

    if page > total_pages:
        page = total_pages

    current_version = versions[page - 1]
    current_game = current_version["game"]

    version_data = load_version_data(current_game)

    reviews = (
        Review.query
        .filter(Review.game_id == conflict.original_game_id)
        .order_by(Review.created_at.desc())
        .all()
    )

    status_label = STATUS_LABELS.get(
        current_game.status,
        current_game.status,
    )

    return render_template(
        "moderation/conflict.html",
        conflict=conflict,
        versions=versions,
        current_version=current_version,
        current_page=page,
        total_pages=total_pages,
        version_data=version_data,
        reviews=reviews,
        status_label=status_label,
        result_label=result_label,
    )


@moderation_bp.route("/<int:conflict_id>/release", methods=["POST"])
@moderator_required
def release_conflict_view(conflict_id):
    conflict = db.session.get(GameConflict, conflict_id)

    if conflict is None:
        abort(404)

    if conflict.viewed_by != g.current_user.id:
        abort(403)

    release_lock(conflict, g.current_user)
    db.session.commit()

    return "", 204


@moderation_bp.route("/<int:conflict_id>/heartbeat", methods=["POST"])
@moderator_required
def heartbeat_conflict_view(conflict_id):
    conflict = db.session.get(GameConflict, conflict_id)

    if conflict is None:
        abort(404)

    if conflict.viewed_by != g.current_user.id:
        abort(403)

    update_lock_heartbeat(conflict, g.current_user)
    db.session.commit()

    return "", 204


@moderation_bp.route("/game/<int:game_id>")
@moderator_required
def game_view(game_id):
    game = db.session.get(Game, game_id)

    if game is None:
        abort(404)

    if game.status not in ("OFFICIAL", "CANCELLED"):
        abort(404)

    version_data = load_version_data(game)

    reviews = (
        Review.query
        .filter(Review.game_id == game.id)
        .order_by(Review.created_at.desc())
        .all()
    )

    status_label = STATUS_LABELS.get(
        game.status,
        game.status,
    )

    return render_template(
        "moderation/game.html",
        game=game,
        version_data=version_data,
        reviews=reviews,
        status_label=status_label,
        result_label=result_label,
    )


@moderation_bp.route("/<int:conflict_id>/finalize", methods=["POST"])
@moderator_required
def finalize_conflict(conflict_id):
    conflict = db.session.get(GameConflict, conflict_id)

    if conflict is None:
        abort(404)

    if conflict.status != "OPEN":
        flash("Партия уже обработана.")
        return redirect(url_for("moderation.index"))

    if (
        conflict.viewed_by != g.current_user.id
        and not is_lock_expired(conflict)
    ):
        flash("Партия обрабатывается другим модератором.")
        return redirect(
            url_for(
                "moderation.conflict_view",
                conflict_id=conflict.id,
            )
        )

    version_id = request.form.get("version", type=int)

    if version_id is None:
        abort(400)

    versions = load_versions(conflict)
    version_ids = [version["game"].id for version in versions]

    if version_id not in version_ids:
        abort(400)

    game = db.session.get(Game, version_id)

    if game is None:
        abort(404)

    release_lock(conflict, g.current_user)

    finalized_game_id = finalize_by_moderator(conflict, game)

    db.session.commit()

    flash("Версия признана официальной.")

    return redirect(
        url_for(
            "moderation.game_view",
            game_id=finalized_game_id,
        )
    )


@moderation_bp.route("/<int:conflict_id>/cancel", methods=["POST"])
@moderator_required
def cancel_conflict_view(conflict_id):
    conflict = db.session.get(GameConflict, conflict_id)

    if conflict is None:
        abort(404)

    if conflict.status != "OPEN":
        flash("Партия уже обработана.")
        return redirect(url_for("moderation.index"))

    if (
        conflict.viewed_by != g.current_user.id
        and not is_lock_expired(conflict)
    ):
        flash("Партия обрабатывается другим модератором.")
        return redirect(
            url_for(
                "moderation.conflict_view",
                conflict_id=conflict.id,
            )
        )

    release_lock(conflict, g.current_user)

    cancel_conflict(conflict)

    db.session.commit()

    flash("Партия отменена.")

    return redirect(url_for("moderation.index"))


@moderation_bp.route("/game/<int:game_id>/cancel", methods=["POST"])
@moderator_required
def cancel_game_view(game_id):
    game = db.session.get(Game, game_id)

    if game is None:
        abort(404)

    if game.status != "OFFICIAL":
        flash("Эту партию нельзя отменить — она уже не официальная.")
        return redirect(
            url_for(
                "moderation.game_view",
                game_id=game.id,
            )
        )

    cancel_official_game(game)

    db.session.commit()

    flash("Партия отменена.")

    return redirect(
        url_for(
            "moderation.game_view",
            game_id=game.id,
        )
    )


@moderation_bp.route("/game/<int:game_id>/restore", methods=["POST"])
@moderator_required
def restore_game_view(game_id):
    game = db.session.get(Game, game_id)

    if game is None:
        abort(404)

    if game.status != "CANCELLED":
        flash("Эту партию нельзя восстановить — она не отменена.")
        return redirect(
            url_for(
                "moderation.game_view",
                game_id=game.id,
            )
        )

    restore_official_game(game)

    db.session.commit()

    flash("Партия восстановлена.")

    return redirect(
        url_for(
            "moderation.game_view",
            game_id=game.id,
        )
    )


@moderation_bp.route("/review/<int:review_id>/clear", methods=["POST"])
@moderator_required
def clear_review_view(review_id):
    review = db.session.get(Review, review_id)

    if review is None:
        abort(404)

    clear_review_text(review)

    db.session.commit()

    flash("Текст отзыва очищен.")

    next_url = request.form.get("next") or request.referrer

    if next_url:
        return redirect(next_url)

    return redirect(url_for("moderation.index"))
