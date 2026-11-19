import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    _database_url = os.getenv("DATABASE_URL")

    if _database_url:
        for _prefix in ("postgres://", "postgresql://"):
            if _database_url.startswith(_prefix):
                _database_url = (
                        "postgresql+psycopg://"
                        + _database_url[len(_prefix):]
                )
                break

        SQLALCHEMY_DATABASE_URI = _database_url
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql+psycopg://"
            f"{os.getenv('DB_USER')}:"
            f"{os.getenv('DB_PASSWORD')}@"
            f"{os.getenv('DB_HOST', 'localhost')}:"
            f"{os.getenv('DB_PORT', '5432')}/"
            f"{os.getenv('DB_NAME')}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    MODERATION_LOCK_TIMEOUT = 90