import re

from app.extensions import db
from app.models import (
    FactionList,
    FactionListFaction,
)


TEAM_PATTERN = re.compile(
    r"^teams\[(\d+)\]\[(\w+)\]"
    r"(?:\[(\d+)\]\[(\w+)\])?"
    r"(\[\])?$"
)


def parse_teams_form(form):
    teams = {}

    for key in form.keys():
        match = TEAM_PATTERN.match(key)
        if not match:
            continue

        team_index = int(match.group(1))
        field = match.group(2)
        player_index = match.group(3)
        player_field = match.group(4)

        teams.setdefault(team_index, {})
        team = teams[team_index]

        if player_index is None:
            if field == "players":
                continue
            team[field] = form.get(key, "")
        else:
            team.setdefault("players", {})
            players = team["players"]
            players.setdefault(int(player_index), {})
            player = players[int(player_index)]

            if key.endswith("[]"):
                player.setdefault(player_field, []).extend(
                    form.getlist(key)
                )
            else:
                player[player_field] = form.get(key, "")

    result = []

    for index in sorted(teams.keys()):
        team = teams[index]

        players = []
        raw_players = team.get("players", {})

        for player_index in sorted(raw_players.keys()):
            players.append(raw_players[player_index])

        result.append({
            "name": team.get("name", ""),
            "command_number": team.get("command_number", ""),
            "score": team.get("score", ""),
            "result": team.get("result", ""),
            "players": players,
        })

    return {
        index: result[index]
        for index in range(len(result))
    }


def form_to_json(form):
    result = {}

    for key in form.keys():
        values = form.getlist(key)

        if len(values) > 1:
            result[key] = values
        elif values:
            result[key] = values[0]

    return result


def build_form_snapshot(form, players_by_id=None):
    snapshot = form_to_json(form)

    if players_by_id is None:
        return snapshot

    for key in list(snapshot.keys()):
        if not key.endswith("[id]"):
            continue

        value = snapshot[key]

        if isinstance(value, list):
            continue

        try:
            player_id = int(value)
        except (TypeError, ValueError):
            continue

        player = players_by_id.get(player_id)

        if player is None:
            continue

        nickname_key = key[:-4] + "[nickname]"
        snapshot[nickname_key] = player.nickname

    return snapshot


def find_or_create_faction_list(faction_ids):
    sorted_ids = sorted(set(faction_ids))

    existing = (
        db.session.query(FactionList.id)
        .join(
            FactionListFaction,
            FactionListFaction.faction_list_id == FactionList.id,
        )
        .group_by(FactionList.id)
        .having(
            db.func.count(FactionListFaction.id) == len(sorted_ids)
        )
        .having(
            db.func.array_agg(
                FactionListFaction.faction_id,
                type_=db.BigInteger,
                order_by=FactionListFaction.faction_id,
            ).op("=")(
                db.cast(sorted_ids, db.ARRAY(db.BigInteger))
            )
        )
        .first()
    )

    if existing is not None:
        return existing[0]

    faction_list = FactionList()
    db.session.add(faction_list)
    db.session.flush()

    for faction_id in sorted_ids:
        db.session.add(
            FactionListFaction(
                faction_list_id=faction_list.id,
                faction_id=faction_id,
            )
        )

    return faction_list.id