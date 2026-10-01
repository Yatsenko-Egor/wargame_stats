from flask import render_template, request

from app.extensions import db
from app.models import (
    Faction,
    FactionListFaction,
    PlayerFactionStatistics,
    Wargame,
    WargameEdition,
)
from app.statistics import statistics_bp
from app.services.game_data import load_faction_list_members


@statistics_bp.route("/factions")
def factions():
    wargames = (
        Wargame.query
        .order_by(Wargame.id)
        .all()
    )

    selected_wargame_id = request.args.get("wargame", type=int)

    wargame_ids = {wargame.id for wargame in wargames}

    if selected_wargame_id not in wargame_ids:
        selected_wargame_id = (
            wargames[0].id
            if wargames
            else None
        )

    available_editions = []

    if selected_wargame_id is not None:
        available_editions = (
            WargameEdition.query
            .filter(WargameEdition.wargame_id == selected_wargame_id)
            .order_by(WargameEdition.id)
            .all()
        )

    selected_edition_id = request.args.get("edition", type=int)

    available_edition_ids = {
        edition.id for edition in available_editions
    }

    if selected_edition_id not in available_edition_ids:
        selected_edition_id = None

    rows = load_faction_stats(
        selected_wargame_id,
        selected_edition_id,
    )

    total_games = sum(row["game_count"] for row in rows)

    return render_template(
        "statistics/factions.html",
        wargames=wargames,
        available_editions=available_editions,
        selected_wargame_id=selected_wargame_id,
        selected_edition_id=selected_edition_id,
        rows=rows,
        total_games=total_games,
    )


def load_faction_stats(wargame_id, edition_id):
    if wargame_id is None:
        return []

    query = (
        db.session.query(
            PlayerFactionStatistics.faction_list_id.label("faction_list_id"),
            db.func.sum(PlayerFactionStatistics.game_count).label("game_count"),
            db.func.sum(PlayerFactionStatistics.wins).label("wins"),
            db.func.sum(PlayerFactionStatistics.losses).label("losses"),
        )
        .join(
            WargameEdition,
            WargameEdition.id == PlayerFactionStatistics.edition_id,
        )
        .filter(WargameEdition.wargame_id == wargame_id)
    )

    if edition_id is not None:
        query = query.filter(
            PlayerFactionStatistics.edition_id == edition_id
        )

    query = query.group_by(PlayerFactionStatistics.faction_list_id)

    stats_rows = query.all()

    if not stats_rows:
        return []

    faction_list_ids = [
        row.faction_list_id for row in stats_rows
    ]

    factions_by_list = load_faction_list_members(faction_list_ids)

    rows = []

    for row in stats_rows:
        factions = factions_by_list.get(row.faction_list_id, [])

        if not factions:
            continue

        faction_names = " + ".join(
            sorted(faction.faction_name for faction in factions)
        )

        game_count = int(row.game_count or 0)
        wins = int(row.wins or 0)

        win_rate = (
            round(wins / game_count * 100, 1)
            if game_count > 0
            else 0.0
        )

        rows.append({
            "faction_names": faction_names,
            "game_count": game_count,
            "wins": wins,
            "win_rate": win_rate,
        })

    rows.sort(
        key=lambda r: (-r["game_count"], r["faction_names"])
    )

    return rows
