from app import db


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(
        db.BigInteger,
        db.Identity(always=True),
        primary_key=True,
    )
    text = db.Column(db.Text)
    rating = db.Column(
        db.SmallInteger,
        nullable=False,
    )
    game_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "game.id",
            ondelete="RESTRICT",
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
    author = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "player.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )

    game = db.relationship(
        "Game",
        back_populates="reviews",
    )

    player = db.relationship(
        "Player",
        back_populates="reviews_received",
        foreign_keys=[player_id],
    )

    author_player = db.relationship(
        "Player",
        back_populates="reviews_written",
        foreign_keys=[author],
    )

    __table_args__ = (
        db.CheckConstraint(
            "rating BETWEEN 1 AND 5",
            name="chk_reviews_rating",
        ),
        db.CheckConstraint(
            "author <> player_id",
            name="chk_reviews_not_self",
        ),
        db.UniqueConstraint(
            "game_id",
            "author",
            "player_id",
            name="uq_reviews_game_author_player",
        ),
        db.Index(
            "idx_reviews_game",
            "game_id",
        ),
        db.Index(
            "idx_reviews_player",
            "player_id",
        ),
        db.Index(
            "idx_reviews_author",
            "author",
        ),
    )