from app import db


class GameVersion(db.Model):
    __tablename__ = "game_version"

    id = db.Column(
        db.BigInteger,
        db.Identity(always=True),
        primary_key=True,
    )
    game_conflict_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "game_conflict.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    game_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "game.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    conflict = db.relationship(
        "GameConflict",
        back_populates="versions",
    )

    game = db.relationship(
        "Game",
        back_populates="versions",
    )

    __table_args__ = (
        db.Index(
            "idx_game_version_conflict",
            "game_conflict_id",
        ),
        db.Index(
            "idx_game_version_game",
            "game_id",
        ),
    )