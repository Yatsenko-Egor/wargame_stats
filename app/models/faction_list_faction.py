from app import db


class FactionListFaction(db.Model):
    __tablename__ = "faction_list_faction"

    id = db.Column(
        db.BigInteger,
        db.Identity(always=True),
        primary_key=True,
    )
    faction_id = db.Column(
        "faction",
        db.BigInteger,
        db.ForeignKey(
            "faction.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    faction_list_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "faction_list.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    faction = db.relationship(
        "Faction",
        back_populates="faction_list_items",
        foreign_keys=[faction_id],
    )

    faction_list = db.relationship(
        "FactionList",
        back_populates="factions",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "faction_list_id",
            "faction",
        ),
    )