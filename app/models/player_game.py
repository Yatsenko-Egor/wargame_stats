from app import db


class PlayerGame(db.Model):
    __tablename__ = "player_game"

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
    team_id = db.Column(
        db.BigInteger,
        db.ForeignKey("team.id", ondelete="CASCADE"),
        nullable=False,
    )

    player = db.relationship(
        "Player",
        back_populates="games",
    )

    team = db.relationship(
        "Team",
        back_populates="players",
    )

    factions = db.relationship(
        "GameFaction",
        back_populates="player_game",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "player_id",
            "team_id",
            name="uq_player_game",
        ),
        db.Index(
            "idx_player_game_player",
            "player_id",
        ),
        db.Index(
            "idx_player_game_team",
            "team_id",
        ),
    )