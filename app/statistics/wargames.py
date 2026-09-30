from datetime import date, timedelta

from flask import render_template, request

from app.extensions import db
from app.models import Game, Wargame, WargameEdition
from app.statistics import statistics_bp


@statistics_bp.route("/wargames")
def wargames():
    date_from, date_to = parse_period(request)

    active_period = resolve_active_period(
        request,
        date_from,
        date_to,
    )

    rows, total_games = load_wargame_stats(date_from, date_to)

    today = date.today()
    this_month_start = _first_day_of_month(today)
    prev_week_start, prev_week_end = _prev_week_range(today)
    this_year_start = date(today.year, 1, 1)

    return render_template(
        "statistics/wargames.html",
        rows=rows,
        total_games=total_games,
        date_from=date_from,
        date_to=date_to,
        active_period=active_period,
        today=today,
        this_month_start=this_month_start,
        prev_week_start=prev_week_start,
        prev_week_end=prev_week_end,
        this_year_start=this_year_start,
    )


def parse_period(request):
    date_from_raw = request.args.get("date_from", "").strip()
    date_to_raw = request.args.get("date_to", "").strip()

    date_from = None
    date_to = None

    if date_from_raw:
        try:
            date_from = date.fromisoformat(date_from_raw)
        except ValueError:
            date_from = None

    if date_to_raw:
        try:
            date_to = date.fromisoformat(date_to_raw)
        except ValueError:
            date_to = None

    today = date.today()

    if date_from is not None and date_to is None:
        date_to = today

    if date_to is not None and date_from is None:
        date_from = date(2000, 1, 1)

    return date_from, date_to


def resolve_active_period(request, date_from, date_to):
    today = date.today()

    if date_from is None and date_to is None:
        return "all_time"

    if date_from == _first_day_of_month(today) and date_to == today:
        return "this_month"

    prev_week_start, prev_week_end = _prev_week_range(today)

    if date_from == prev_week_start and date_to == prev_week_end:
        return "prev_week"

    if date_from == date(today.year, 1, 1) and date_to == today:
        return "this_year"

    return "custom"

def _first_day_of_month(d):
    return date(d.year, d.month, 1)


def _prev_week_range(today):
    start_this_week = today - timedelta(days=today.weekday())
    end_prev_week = start_this_week - timedelta(days=1)
    start_prev_week = end_prev_week - timedelta(days=6)

    return start_prev_week, end_prev_week


def load_wargame_stats(date_from, date_to):
    query = (
        db.session.query(
            Wargame.id.label("wargame_id"),
            Wargame.name.label("wargame_name"),
            db.func.count(Game.id).label("game_count"),
        )
        .select_from(Game)
        .join(
            WargameEdition,
            WargameEdition.id == Game.edition_id,
        )
        .join(
            Wargame,
            Wargame.id == WargameEdition.wargame_id,
        )
        .filter(Game.status == "OFFICIAL")
    )

    if date_from is not None:
        query = query.filter(Game.date >= date_from)

    if date_to is not None:
        query = query.filter(Game.date <= date_to)

    query = query.group_by(Wargame.id, Wargame.name)

    results = query.all()

    total_games = sum(row.game_count for row in results)

    rows = []

    for row in results:
        percentage = (
            row.game_count / total_games * 100
            if total_games > 0
            else 0
        )

        rows.append({
            "wargame_id": row.wargame_id,
            "wargame_name": row.wargame_name,
            "game_count": row.game_count,
            "percentage": round(percentage, 1),
        })

    rows.sort(key=lambda r: r["game_count"], reverse=True)

    return rows, total_games
