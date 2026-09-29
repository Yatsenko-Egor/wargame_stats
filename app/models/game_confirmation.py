from app import db


confirmation_response = db.Enum(
    "CONFIRM",
    "CONFLICT",
    "WAIT",
    name="confirmation_response",
)


class GameConfirmation(db.Model):
    __tablename__ = "game_confirmation"

    id = db.Column(
        db.BigInteger,
        db.Identity(always=True),
        primary_key=True,
    )
    game_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "game.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    player_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "player.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    response = db.Column(
        confirmation_response,
        nullable=False,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )

    game = db.relationship(
        "Game",
        back_populates="confirmations",
    )

    player = db.relationship(
        "Player",
        back_populates="confirmations",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "game_id",
            "player_id",
            name="uq_game_confirmation",
        ),
        db.Index(
            "idx_game_confirmation_game",
            "game_id",
        ),
        db.Index(
            "idx_game_confirmation_player",
            "player_id",
        ),
    )