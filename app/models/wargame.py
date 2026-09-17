from app import db


class Wargame(db.Model):
    __tablename__ = "wargame"

    id = db.Column(
        db.BigInteger,
        db.Identity(always=True),
        primary_key=True,
    )
    name = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
    )

    editions = db.relationship(
        "WargameEdition",
        back_populates="wargame",
    )

    factions = db.relationship(
        "Faction",
        back_populates="wargame",
    )