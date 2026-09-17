from app import db


class WargameEdition(db.Model):
    __tablename__ = "wargame_edition"

    id = db.Column(
        db.BigInteger,
        db.Identity(always=True),
        primary_key=True,
    )
    edition_name = db.Column(
        db.String(255),
        nullable=False,
    )
    wargame_id = db.Column(
        db.BigInteger,
        db.ForeignKey("wargame.id", ondelete="RESTRICT"),
        nullable=False,
    )

    wargame = db.relationship(
        "Wargame",
        back_populates="editions",
    )

    games = db.relationship(
        "Game",
        back_populates="edition",
    )

    faction_statistics = db.relationship(
        "PlayerFactionStatistics",
        back_populates="edition",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "wargame_id",
            "edition_name",
            name="uq_wargame_edition",
        ),
    )