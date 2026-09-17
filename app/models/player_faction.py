from app import db


class PlayerFaction(db.Model):
    __tablename__ = "player_faction"

    id = db.Column(
        db.BigInteger,
        db.Identity(always=True),
        primary_key=True,
    )
    player_id = db.Column(
        db.BigInteger,
        db.ForeignKey("player.id", ondelete="CASCADE"),
        nullable=False,
    )
    faction_id = db.Column(
        db.BigInteger,
        db.ForeignKey("faction.id", ondelete="RESTRICT"),
        nullable=False,
    )

    player = db.relationship(
        "Player",
        back_populates="factions",
    )

    faction = db.relationship(
        "Faction",
        back_populates="player_factions",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "player_id",
            "faction_id",
            name="uq_player_faction",
        ),
    )