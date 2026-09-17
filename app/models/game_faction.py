from app import db


class GameFaction(db.Model):
    __tablename__ = "game_faction"

    id = db.Column(
        db.BigInteger,
        db.Identity(always=True),
        primary_key=True,
    )
    player_game_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "player_game.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    faction_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "faction.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    player_game = db.relationship(
        "PlayerGame",
        back_populates="factions",
    )

    faction = db.relationship(
        "Faction",
        back_populates="game_factions",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "player_game_id",
            "faction_id",
            name="uq_game_faction",
        ),
        db.Index(
            "idx_game_faction_player_game",
            "player_game_id",
        ),
        db.Index(
            "idx_game_faction_faction",
            "faction_id",
        ),
    )