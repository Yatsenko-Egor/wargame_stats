from app import db


team_result = db.Enum(
    "WIN",
    "LOSS",
    "DRAW",
    name="team_result",
)


class Team(db.Model):
    __tablename__ = "team"

    id = db.Column(
        db.BigInteger,
        db.Identity(always=True),
        primary_key=True,
    )
    game_id = db.Column(
        "game",
        db.BigInteger,
        db.ForeignKey("game.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(
        db.String(255),
        nullable=False,
    )
    command_number = db.Column(
        db.Integer,
        nullable=False,
    )
    result = db.Column(team_result)
    score = db.Column(db.Integer)

    game = db.relationship(
        "Game",
        back_populates="teams",
        foreign_keys=[game_id],
    )

    players = db.relationship(
        "PlayerGame",
        back_populates="team",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "game",
            "command_number",
            name="uq_team_number",
        ),
        db.CheckConstraint(
            "command_number > 0",
            name="chk_team_command_number",
        ),
        db.CheckConstraint(
            "score IS NULL OR score >= 0",
            name="chk_team_score",
        ),
        db.Index(
            "idx_team_game",
            "game",
        ),
    )