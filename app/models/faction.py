from app import db


class Faction(db.Model):
    __tablename__ = "faction"

    id = db.Column(
        db.BigInteger,
        db.Identity(always=True),
        primary_key=True,
    )
    wargame_id = db.Column(
        db.BigInteger,
        db.ForeignKey("wargame.id", ondelete="RESTRICT"),
        nullable=False,
    )
    faction_name = db.Column(
        db.String(255),
        nullable=False,
    )

    wargame = db.relationship(
        "Wargame",
        back_populates="factions",
    )

    player_factions = db.relationship(
        "PlayerFaction",
        back_populates="faction",
    )

    game_factions = db.relationship(
        "GameFaction",
        back_populates="faction",
    )

    faction_list_items = db.relationship(
        "FactionListFaction",
        back_populates="faction",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "wargame_id",
            "faction_name",
            name="uq_faction_wargame_name",
        ),
    )