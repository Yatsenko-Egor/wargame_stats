import os

from flask import Flask, g, flash, redirect, url_for

from config import Config
from app.extensions import db, migrate
from app.auth import auth_bp
from app.profile import profile_bp
from app.auth.session import get_current_user
from app.games import games_bp
from app.confirm import confirm_bp
from app.statistics import statistics_bp
from app.players import players_bp
from app.moderation import moderation_bp
from app.admin import admin_bp


def create_app():
    app = Flask(__name__)

    os.makedirs(
        os.path.join(app.static_folder, "uploads", "avatars"),
        exist_ok=True,
    )

    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(games_bp)
    app.register_blueprint(confirm_bp)
    app.register_blueprint(statistics_bp)
    app.register_blueprint(players_bp)
    app.register_blueprint(moderation_bp)
    app.register_blueprint(admin_bp)

    @app.before_request
    def load_current_user():
        g.current_user = get_current_user()

        if g.current_user is not None and g.current_user.is_deleted:
            from app.auth.session import logout_user

            logout_user()
            g.current_user = None
            flash("Ваш аккаунт удалён.")
            return redirect(url_for("auth.login"))

    @app.context_processor
    def inject_current_user():
        return {
            "current_user": g.current_user,
        }

    return app