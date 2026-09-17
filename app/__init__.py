from flask import Flask, g

from config import Config
from app.extensions import db, migrate
from app.auth import auth_bp
from app.profile import profile_bp
from app.auth.session import get_current_user


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)

    @app.before_request
    def load_current_user():
        g.current_user = get_current_user()

    @app.context_processor
    def inject_current_user():
        return {
            "current_user": g.current_user,
        }

    return app