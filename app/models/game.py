from app import db


game_status = db.Enum(
    "PENDING",
    "OFFICIAL",
    "CANCELLED",
    "MODERATION",
    name="game_status",
)


class Game(db.Model):
    __tablename__ = "game"

    id = db.Column(
        db.BigInteger,
        db.Identity(always=True),
        primary_key=True,
    )
    command_count = db.Column(
        db.Integer,
        nullable=False,
    )
    roster_points = db.Column(
        db.Integer,
        nullable=False,
    )
    status = db.Column(
        game_status,
        nullable=False,
        server_default="PENDING",
    )
    date = db.Column(
        db.Date,
        nullable=False,
    )
    edition_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "wargame_edition.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_by = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "player.id",
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

    edition = db.relationship(
        "WargameEdition",
        back_populates="games",
    )

    creator = db.relationship(
        "Player",
        back_populates="created_games",
        foreign_keys=[created_by],
    )

    teams = db.relationship(
        "Team",
        back_populates="game",
        cascade="all, delete-orphan",
    )

    confirmations = db.relationship(
        "GameConfirmation",
        back_populates="game",
        cascade="all, delete-orphan",
    )

    versions = db.relationship(
        "GameVersion",
        back_populates="game",
    )

    reviews = db.relationship(
        "Review",
        back_populates="game",
    )

    __table_args__ = (
        db.CheckConstraint(
            "command_count >= 2",
            name="chk_game_command_count",
        ),
        db.CheckConstraint(
            "roster_points > 0",
            name="chk_game_roster_points",
        ),
        db.Index(
            "idx_game_edition",
            "edition_id",
        ),
        db.Index(
            "idx_game_date",
            "date",
        ),
        db.Index(
            "idx_game_status",
            "status",
        ),
        db.Index(
            "idx_game_created_by",
            "created_by",
        ),
    )