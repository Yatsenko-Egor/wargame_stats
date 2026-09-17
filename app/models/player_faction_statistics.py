from app import db


class PlayerFactionStatistics(db.Model):
    __tablename__ = "player_faction_statistics"

    faction_list_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "faction_list.id",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    )
    player_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "player.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    edition_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "wargame_edition.id",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    )
    game_count = db.Column(
        db.Integer,
        nullable=False,
        server_default="0",
    )
    wins = db.Column(
        db.Integer,
        nullable=False,
        server_default="0",
    )
    losses = db.Column(
        db.Integer,
        nullable=False,
        server_default="0",
    )

    faction_list = db.relationship(
        "FactionList",
        back_populates="statistics",
    )

    player = db.relationship(
        "Player",
        back_populates="faction_statistics",
    )

    edition = db.relationship(
        "WargameEdition",
        back_populates="faction_statistics",
    )

    __table_args__ = (
        db.CheckConstraint(
            "game_count >= 0",
            name="chk_pfs_game_count",
        ),
        db.CheckConstraint(
            "wins >= 0",
            name="chk_pfs_wins",
        ),
        db.CheckConstraint(
            "losses >= 0",
            name="chk_pfs_losses",
        ),
        db.CheckConstraint(
            "wins + losses <= game_count",
            name="chk_pfs_results",
        ),
        db.Index(
            "idx_pfs_player",
            "player_id",
        ),
        db.Index(
            "idx_pfs_edition",
            "edition_id",
        ),
    )