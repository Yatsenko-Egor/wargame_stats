from sqlalchemy import text

from app import db


player_role = db.Enum(
    "USER",
    "MODERATOR",
    "ADMIN",
    name="player_role",
)


class Player(db.Model):
    __tablename__ = "player"

    id = db.Column(
        db.BigInteger,
        db.Identity(always=True),
        primary_key=True,
    )
    nickname = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
    )
    email = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
    )
    hash_password = db.Column(
        db.Text,
        nullable=False,
    )
    role = db.Column(
        player_role,
        nullable=False,
        server_default="USER",
    )
    avatar_url = db.Column(db.Text)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    factions = db.relationship(
        "PlayerFaction",
        back_populates="player",
        cascade="all, delete-orphan",
    )

    games = db.relationship(
        "PlayerGame",
        back_populates="player",
        cascade="all, delete-orphan",
    )

    confirmations = db.relationship(
        "GameConfirmation",
        back_populates="player",
    )

    created_games = db.relationship(
        "Game",
        back_populates="creator",
        foreign_keys="Game.created_by",
    )

    reviews_written = db.relationship(
        "Review",
        back_populates="author_player",
        foreign_keys="Review.author",
    )

    reviews_received = db.relationship(
        "Review",
        back_populates="player",
        foreign_keys="Review.player_id",
    )

    faction_statistics = db.relationship(
        "PlayerFactionStatistics",
        back_populates="player",
        cascade="all, delete-orphan",
    )