from app import db


game_conflict_status = db.Enum(
    "OPEN",
    "RESOLVED",
    name="game_conflict_status",
)


class GameConflict(db.Model):
    __tablename__ = "game_conflict"

    id = db.Column(
        db.BigInteger,
        db.Identity(always=True),
        primary_key=True,
    )
    original_game_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "game.id",
            ondelete="RESTRICT",
        ),
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
    status = db.Column(
        game_conflict_status,
        nullable=False,
        server_default="OPEN",
    )

    original_game = db.relationship(
        "Game",
        foreign_keys=[original_game_id],
        viewonly=True,
    )

    versions = db.relationship(
        "GameVersion",
        back_populates="conflict",
        cascade="all, delete-orphan",
    )