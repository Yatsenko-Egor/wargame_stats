from app import db


class FactionList(db.Model):
    __tablename__ = "faction_list"

    id = db.Column(
        db.BigInteger,
        db.Identity(always=True),
        primary_key=True,
    )

    factions = db.relationship(
        "FactionListFaction",
        back_populates="faction_list",
        cascade="all, delete-orphan",
    )

    statistics = db.relationship(
        "PlayerFactionStatistics",
        back_populates="faction_list",
    )