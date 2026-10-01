from flask import Flask, g

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


def create_app():
    app = Flask(__name__)

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

    @app.before_request
    def load_current_user():
        g.current_user = get_current_user()

    @app.context_processor
    def inject_current_user():
        return {
            "current_user": g.current_user,
        }

    return app