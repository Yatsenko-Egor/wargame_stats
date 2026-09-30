from flask import render_template, request

from app.extensions import db
from app.models import Game, Player, Review
from app.players import players_bp


PER_PAGE = 30


@players_bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "desc")
    page = request.args.get("page", default=1, type=int)

    if sort not in ("asc", "desc"):
        sort = "desc"

    all_players = load_players_with_rating(q)

    rated = [
        player for player in all_players
        if player["rating"] is not None
    ]

    unrated = [
        player for player in all_players
        if player["rating"] is None
    ]

    rated.sort(
        key=lambda item: item["rating"],
        reverse=(sort != "asc"),
    )

    players_sorted = rated + unrated

    total_count = len(players_sorted)
    total_pages = max(1, (total_count + PER_PAGE - 1) // PER_PAGE)

    if page < 1:
        page = 1

    if page > total_pages:
        page = total_pages

    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE

    page_players = players_sorted[start:end]

    return render_template(
        "players/list.html",
        players=page_players,
        q=q,
        sort=sort,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
    )


def load_players_with_rating(q):
    official_game_ids = (
        db.session.query(Game.id)
        .filter(Game.status == "OFFICIAL")
        .scalar_subquery()
    )

    query = (
        db.session.query(
            Player.id.label("player_id"),
            Player.nickname.label("nickname"),
            db.func.avg(Review.rating).label("rating"),
            db.func.count(Review.id).label("rating_count"),
        )
        .outerjoin(
            Review,
            (Review.player_id == Player.id)
            & (Review.game_id.in_(official_game_ids)),
        )
    )

    if q:
        query = query.filter(Player.nickname.ilike(f"%{q}%"))

    query = query.group_by(Player.id, Player.nickname)

    rows = query.all()

    players_with_rating = []
    players_without_rating = []

    for row in rows:
        rating_value = row.rating
        rating_count = row.rating_count or 0

        if rating_value is None or rating_count == 0:
            players_without_rating.append({
                "player_id": row.player_id,
                "nickname": row.nickname,
                "rating": None,
                "rating_count": 0,
            })
            continue

        players_with_rating.append({
            "player_id": row.player_id,
            "nickname": row.nickname,
            "rating": round(float(rating_value), 1),
            "rating_count": rating_count,
        })

    players_with_rating.sort(key=lambda item: item["nickname"])
    players_without_rating.sort(key=lambda item: item["nickname"])

    return players_with_rating + players_without_rating